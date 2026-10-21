"""Real browser evidence. Controlled state injection is explicitly identified per check."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run_browser_qa(url: str, directory: Path, fixture: dict | None = None) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    checks, errors, failed_assets = [], [], []
    def record(name, passed, detail, category="gameplay", critical=True):
        checks.append({"id":name,"passed":bool(passed),"critical":critical,"category":category,"details":detail})
        (directory/'qa_progress.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    def finish_report():
        report={'overall':'PASS' if checks and all(c['passed'] for c in checks if c['critical']) else 'FAIL','checks':checks,
                'page_errors':errors,'screenshot':'gameplay.png','scope':'Controlled-position functional browser verification, not autonomous completion or enjoyment assessment.'}
        (directory/'qa_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        return report
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width":1440,"height":1000}, device_scale_factor=1)
        if fixture is not None:
            # Exercise the real preview/runtime with a deterministic local specification.
            page.route('**/fixtures/*.json', lambda route: route.fulfill(json=fixture))
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('response', lambda response: failed_assets.append(response.url) if response.status>=400 and '/assets/' in response.url else None)
        try:
            page.goto(url + ('&' if '?' in url else '?') + 'test=1', wait_until='domcontentloaded', timeout=25000)
            page.wait_for_function('window.__AETHER_PLATFORMER__ && document.querySelector("canvas")',timeout=25000)
            snap=lambda:page.evaluate('window.__AETHER_PLATFORMER__.snapshot()')
            teleport=lambda x,y:page.evaluate('([x,y])=>window.__AETHER_PLATFORMER__.teleport(x,y)',[x,y])
            def press(key):
                page.keyboard.down(key);page.wait_for_timeout(85);page.keyboard.up(key)
            def wait_grounded():
                page.wait_for_function('window.__AETHER_PLATFORMER__?.snapshot().ready && window.__AETHER_PLATFORMER__.snapshot().grounded',timeout=4000)
            def restart(level=0):
                generation=snap()['generation']
                page.evaluate('(level)=>window.__AETHER_PLATFORMER__.restart(level)',level)
                page.wait_for_function('(n)=>window.__AETHER_PLATFORMER__?.snapshot().ready && window.__AETHER_PLATFORMER__.snapshot().generation>n',arg=generation,timeout=4000)
                wait_grounded()
            if '/studio/play/' in url:
                gid=url.split('/studio/play/')[1].split('?')[0]
                spec=page.evaluate('(id)=>fetch(`/api/v2/games/${id}/spec`).then(r=>r.json())',gid)
            else:
                from urllib.parse import parse_qs,urlparse
                name=parse_qs(urlparse(url).query).get('example',['forest'])[0]
                spec=page.evaluate('(name)=>fetch(`/fixtures/${name}.json`).then(r=>r.json())',name)
            from services.gameplay_qa import uses_components, verify_gameplay
            if uses_components(spec):
                verify_gameplay(page,spec,directory,record)
                record('canvas_and_assets',not snap()['missingAssets'] and not failed_assets,{'missing':snap()['missingAssets'],'http_failures':failed_assets},'runtime')
                record('no_runtime_exceptions',not errors,errors,'runtime')
                return finish_report()
            page.locator('canvas').click()
            page.wait_for_timeout(400)
            record('canvas_and_assets',not snap()['missingAssets'] and not failed_assets,{'missing':snap()['missingAssets'],'http_failures':failed_assets},'runtime')
            before=snap();page.keyboard.down('ArrowRight')
            page.wait_for_function('(x)=>window.__AETHER_PLATFORMER__.snapshot().x>x+25',arg=before['x'],timeout=2500)
            page.keyboard.up('ArrowRight');after=snap()
            record('horizontal_movement',after['x']>before['x']+20,{'before':before,'after':after})
            restart();page.wait_for_timeout(150);before=snap()
            press('Space');page.wait_for_timeout(180);apex=snap();wait_grounded();landed=snap()
            record('jump_gravity_landing',apex['y']<before['y']-20 and landed['grounded'] and abs(landed['y']-before['y'])<6,{'before':before,'airborne':apex,'landed':landed})
            if 'double_jump' in spec['player']['abilities']:
                restart();press('Space');page.wait_for_timeout(160);before_second=snap();press('Space');after_second=snap()
                record('double_jump',after_second['vy'] < before_second['vy']-60,{'before_second_jump':before_second,'after_second_jump':after_second})
                restart()
            if 'dash' in spec['player']['abilities']:
                start=snap();page.keyboard.down('Shift')
                page.wait_for_function('Math.abs(window.__AETHER_PLATFORMER__.snapshot().vx)>450',timeout=1500)
                peak=snap();page.keyboard.up('Shift');page.wait_for_timeout(220);dashed=snap()
                record('dash',peak['vx']>450 and dashed['x']>start['x']+35,{'before':start,'peak':peak,'after':dashed});restart()
            environment=snap()
            record('environment_composition',environment['environment']==spec['theme'] and not environment['missingAssets'],
                   {'theme':spec['theme'],'method':'Runtime theme/asset witness; screenshots require human visual review'},'fidelity')
            if spec['theme']=='ice':
                record('ice_composition',environment['environment']=='ice' and environment.get('terrainTexture')=='ice',environment,'fidelity')
            if spec.get('exit_indicator','none')!='none':
                values=[]
                for _ in range(8):
                    values.append(snap()['exitAlpha']);page.wait_for_timeout(90)
                record('exit_indicator_animation',max(values)-min(values)>.12 and snap()['exitStyle']==spec.get('exit_style','gate'),
                       {'mode':spec['exit_indicator'],'style':snap()['exitStyle'],'observed_alpha':values},'fidelity')
            if spec.get('slippery'):
                restart();page.keyboard.down('ArrowRight');page.wait_for_timeout(350);page.keyboard.up('ArrowRight')
                before=snap();page.wait_for_timeout(150);after=snap()
                record('slippery_momentum',after['x']-before['x']>15 and after['vx']>70,{'released':before,'after':after},'fidelity');restart()
            if any(p['moving'] for p in spec['platforms']):
                before=snap()['movingPlatforms'];page.wait_for_timeout(450);after=snap()['movingPlatforms']
                record('moving_platform_motion',any(abs(a['x']-b['x'])>5 for a,b in zip(before,after)),{'before':before,'after':after},'fidelity')
            def verify_encounters(stage_spec, stage=0):
                for behavior in sorted({e.get('behavior','patrol') for e in stage_spec['entities'] if e['kind']=='enemy'}):
                    restart(stage)
                    enemy=next(e for e in stage_spec['entities'] if e['kind']=='enemy' and e.get('behavior','patrol')==behavior)
                    if behavior=='patrol':
                        before=next(e for e in snap()['enemies'] if e['behavior']=='patrol');page.wait_for_timeout(350)
                        after=next(e for e in snap()['enemies'] if e['behavior']=='patrol')
                        passed=abs(before['x']-after['x'])>5
                    elif behavior=='chase':
                        teleport(enemy['x']-85,enemy['y']);page.wait_for_timeout(180)
                        before=next(e for e in snap()['enemies'] if e['behavior']=='chase')
                        teleport(enemy['x']+60,enemy['y']);page.wait_for_timeout(100)
                        after=next(e for e in snap()['enemies'] if e['behavior']=='chase')
                        passed=before['vx']<0 and after['vx']>=0
                    else:
                        platform=stage_spec['platforms'][enemy['platform']]
                        player_x=max(platform['x']*36+25,enemy['x']-100)
                        if enemy['x']-player_x<60: player_x=min((platform['x']+platform['width'])*36-25,enemy['x']+100)
                        teleport(player_x,platform['y']*36-28);before=snap();page.wait_for_timeout(1900);after=snap()
                        passed=after['shotsFired']>before['shotsFired'] and after['health']<before['health']
                    record('enemy_'+behavior,passed,{'method':'Controlled player positioning; real enemy simulation and projectile collisions','before':before,'after':after},'fidelity')
                if any(e['kind']=='enemy' for e in stage_spec['entities']):
                    record('enemy_behaviors',all(c['passed'] for c in checks if c['id'].startswith('enemy_')),{'behaviors':sorted({e.get('behavior','patrol') for e in stage_spec['entities'] if e['kind']=='enemy'})},'fidelity')
            verify_encounters(spec)
            if any(e['kind']=='timed_hazard' for e in spec['entities']):
                restart();values=[]
                for _ in range(14):
                    values.append(snap()['machines'][0]['active']);page.wait_for_timeout(180)
                record('timed_hazard_cycle',len(set(values))==2,{'observed_active':values},'fidelity')
                hazard=next(e for e in spec['entities'] if e['kind']=='timed_hazard')
                teleport(hazard['x'],hazard['y']);before=snap()
                for _ in range(16):
                    page.wait_for_timeout(150)
                    if snap()['health']<before['health']:break
                record('timed_hazard_damage',snap()['health']<before['health'],{'method':'Controlled positioning in real timed hazard; actual collision and damage','before':before,'after':snap()},'fidelity')
            if any(e['kind']=='icicle' for e in spec['entities']):
                restart();trap=next((e for e in spec['entities'] if e['kind']=='icicle' and e.get('trigger')=='proximity'),next(e for e in spec['entities'] if e['kind']=='icicle'))
                platform=spec['platforms'][trap['platform']]
                before=snap();teleport(trap['x'],platform['y']*36-28)
                if trap.get('trigger')=='timer':
                    page.wait_for_function('window.__AETHER_PLATFORMER__.snapshot().icicles[0].state==="warning"',timeout=trap.get('period_ms',2200)+2000)
                samples=[]
                for _ in range(22):
                    page.wait_for_timeout(130);samples.append(snap())
                states={t['icicles'][0]['state'] for t in samples}
                record('falling_icicle_cycle',{'warning','falling','spent'}<=states and any(t['health']<before['health'] for t in samples),
                       {'method':('Configured timer' if trap.get('trigger')=='timer' else 'Player enters proximity trigger')+'; real warning, falling physics, terrain collision and player damage',
                        'trigger':trap.get('trigger'),'period_ms':trap.get('period_ms',2200),'states':sorted(states),'samples':samples},'fidelity')
                page.screenshot(path=str(directory/'icicle.png'),full_page=True)
                teleport(spec['spawn']['x'],spec['spawn']['y'])
                page.wait_for_function('window.__AETHER_PLATFORMER__.snapshot().icicles[0].state==="waiting"',timeout=trap.get('period_ms',2200)+1500)
                record('falling_icicle_reset',snap()['icicles'][0]['state']=='waiting',{'method':'Leave proximity volume after terrain collision and observe cooldown/reset','snapshot':snap()},'fidelity')
                restart();timer_traps=[e for e in spec['entities'] if e['kind']=='icicle' and e.get('trigger')=='timer']
                if timer_traps:
                    page.wait_for_function('window.__AETHER_PLATFORMER__.snapshot().icicles.some(t=>t.trigger==="timer"&&t.activations>0)',timeout=max(e.get('period_ms',2200) for e in timer_traps)+2500)
                    record('timer_icicle',any(t['activations']>0 for t in snap()['icicles'] if t['trigger']=='timer'),snap(),'fidelity')
            restart()
            page.screenshot(path=str(directory/'environment.png'),full_page=True)
            # Exercise every mandatory edge with actual keyboard and gravity.
            # Isolated launch positioning prevents earlier damage from masking later edge defects.
            def verify_route(stage_spec, stage=0):
                route=[p for p in stage_spec['platforms'] if not p['moving'] and p.get('route','main')=='main']
                edge_results=[]
                for a,b in zip(route,route[1:]):
                    restart(stage)
                    teleport((a['x']+a['width'])*36-85,a['y']*36-28)
                    wait_grounded()
                    page.keyboard.down('ArrowRight')
                    page.wait_for_function('(edge)=>window.__AETHER_PLATFORMER__.snapshot().x>=edge-25',arg=(a['x']+a['width'])*36,timeout=3000)
                    press('Space')
                    target=(b['x']+1.0)*36
                    # Stop horizontally above a safe landing point, clear of central hazards.
                    for _ in range(35):
                        page.wait_for_timeout(40)
                        if snap()['x']>=target:break
                    page.keyboard.up('ArrowRight')
                    if (stage_spec.get('slippery') if stage_spec.get('slippery') is not None else spec.get('slippery')):
                        # Ice requires active braking; releasing right alone intentionally
                        # preserves momentum and can overshoot precision landings.
                        page.keyboard.down('ArrowLeft')
                        page.wait_for_function('window.__AETHER_PLATFORMER__.snapshot().vx<=20',timeout=1500)
                        page.keyboard.up('ArrowLeft')
                    platform_index=stage_spec['platforms'].index(b)
                    # Optional moving routes can catch a jump above the destination's static floor.
                    # Accept only a settled, physically observed landing on that section's registered route.
                    surfaces=[p['y']*36 for p in stage_spec['platforms'] if (p['moving'] or p.get('route')=='optional') and b['x']<=p['x']<b['x']+b['width']]
                    target_info={'index':platform_index,'left':b['x']*36,'right':(b['x']+b['width'])*36,'surfaces':surfaces,
                                 'exit':any(e['kind']=='exit' and e['platform']==platform_index for e in stage_spec['entities']), 'stage':stage}
                    predicate='''(t)=>{const s=window.__AETHER_PLATFORMER__.snapshot();return s.landedPlatforms.includes(t.index)||(s.state==='playing'&&s.grounded&&s.x>t.left&&s.x<t.right&&t.surfaces.some(y=>Math.abs(s.y+24-y)<8))||(t.exit&&s.levelIndex===t.stage&&['won','transitioning'].includes(s.state)&&s.x>t.left&&s.x<t.right);}'''
                    try:page.wait_for_function(predicate,arg=target_info,timeout=4000)
                    except Exception:pass
                    result=snap()
                    settled_alternate=result['state']=='playing' and result['grounded'] and target_info['left']<result['x']<target_info['right'] and any(abs(result['y']+24-y)<8 for y in surfaces)
                    exited=target_info['exit'] and result['levelIndex']==stage and result['state'] in ('won','transitioning') and target_info['left']<result['x']<target_info['right']
                    edge_results.append({'from':a['x'],'to':b['x'],'landed':platform_index in result['landedPlatforms'] or settled_alternate or exited,
                                         'route':'exit collision' if exited else 'registered alternate' if settled_alternate else 'static floor','snapshot':result})
                record('mandatory_route_edges',all(e['landed'] for e in edge_results),{'method':'Isolated launch positions; actual keyboard jumps, physics, observed landings or an actual destination exit collision. Registered alternate surfaces are included. This is not a full autonomous playthrough.','edges':edge_results},'level_layout')
            verify_route(spec)
            restart();before=snap()
            crystal=next((e for e in spec['entities'] if e['kind']=='crystal'),None)
            if crystal:
                teleport(crystal['x'],crystal['y']);page.wait_for_timeout(100)
                record('collectible_overlap',snap()['crystals']==1,{'method':'Controlled placement into a real crystal overlap','snapshot':snap()})
            checkpoint=next((e for e in spec['entities'] if e['kind']=='checkpoint'),None)
            if checkpoint:
                teleport(checkpoint['x'],checkpoint['y']);page.wait_for_timeout(100);activated=snap()
                teleport(20,spec['height']+10);page.wait_for_timeout(250);respawn=snap()
                record('checkpoint_respawn',activated['checkpoint']==checkpoint['platform'] and abs(respawn['x']-checkpoint['x'])<10,{'method':'Controlled overlap and fall; actual checkpoint/respawn logic','activated':activated,'respawn':respawn})
            restart()
            gate=next(e for e in spec['entities'] if e['kind']=='exit')
            teleport(gate['x']-110,gate['y']-20);page.wait_for_timeout(600)
            page.screenshot(path=str(directory/'exit-indicator.png'),full_page=True)
            page.wait_for_timeout(220)
            page.screenshot(path=str(directory/'exit-indicator-next.png'),full_page=True)
            restart()
            if spec['objective']['required']:
                teleport(gate['x'],gate['y']);page.wait_for_timeout(80)
                record('locked_exit',snap()['state']=='playing',{'method':'Controlled exit overlap without required crystals','snapshot':snap()})
                restart()
            transitions=[]
            levels=spec.get('levels') or [spec]
            for stage, level in enumerate(levels):
                if stage:
                    page.screenshot(path=str(directory/f'stage-{stage+1}.png'),full_page=True)
                    verify_encounters(level,stage)
                    verify_route(level,stage)
                    restart(stage)
                resolved = {**spec, **{key: value for key, value in level.items() if value is not None}}
                current = snap()
                record('level_settings', current['levelIndex'] == stage and current['environment'] == resolved['theme'] and current['slippery'] == bool(resolved.get('slippery')) and current['objective'] == level['objective'] and current['checkpoint'] == -1 and current['crystals'] == 0,
                       {'stage': stage, 'snapshot': current}, 'fidelity')
                if stage and any(e['kind']=='icicle' for e in level['entities']):
                    trap=next((e for e in level['entities'] if e['kind']=='icicle' and e.get('trigger')=='proximity'),next(e for e in level['entities'] if e['kind']=='icicle'))
                    teleport(trap['x'],level['platforms'][trap['platform']]['y']*36-28)
                    before=snap()
                    trap_index=[e for e in level['entities'] if e['kind']=='icicle'].index(trap)
                    page.wait_for_function('(i)=>window.__AETHER_PLATFORMER__.snapshot().icicles[i].state==="warning"',arg=trap_index,timeout=trap.get('period_ms',2200)+2500)
                    samples=[snap()]
                    for _ in range(22):
                        page.wait_for_timeout(130);samples.append(snap())
                    states={sample['icicles'][trap_index]['state'] for sample in samples}
                    record('falling_icicle_cycle',{'warning','falling','spent'}<=states and any(sample['health']<before['health'] for sample in samples),
                           {'stage':stage,'method':'Controlled positioning under a later-level icicle; real warning, fall, terrain collision and damage','states':sorted(states),'before':before,'after':snap()},'fidelity')
                    restart(stage)
                if stage and any(e['kind']=='timed_hazard' for e in level['entities']):
                    hazard=next(e for e in level['entities'] if e['kind']=='timed_hazard')
                    values=[]
                    for _ in range(14):
                        values.append(snap()['machines'][0]['active']);page.wait_for_timeout(hazard.get('period_ms',2200)/12)
                    record('timed_hazard_cycle',len(set(values))==2,{'stage':stage,'observed_active':values},'fidelity')
                    restart(stage)
                checkpoint=next((e for e in level['entities'] if e['kind']=='checkpoint'),None)
                if stage and checkpoint:
                    teleport(checkpoint['x'],checkpoint['y']);page.wait_for_timeout(100)
                    activated=snap()
                    teleport(20,level['height']+10);page.wait_for_timeout(250)
                    respawn=snap()
                    record('later_checkpoint_respawn',activated['checkpoint']==checkpoint['platform'] and respawn['levelIndex']==stage and abs(respawn['x']-checkpoint['x'])<10,
                           {'method':'Actual later-level checkpoint overlap and fall, controlled positions','activated':activated,'respawn':respawn})
                    restart(stage)
                for entity in level['entities']:
                    if entity['kind']=='crystal':
                        teleport(entity['x'],entity['y']);page.wait_for_timeout(50)
                gate=next(e for e in level['entities'] if e['kind']=='exit')
                teleport(gate['x'],gate['y'])
                if stage+1<len(levels):
                    page.wait_for_function('(i)=>window.__AETHER_PLATFORMER__?.snapshot().levelIndex===i',arg=stage+1,timeout=4000)
                    transitions.append({'from':stage,'to':snap()['levelIndex'],'snapshot':snap()})
                    wait_grounded()
                    record('transition_reset',snap()['crystals']==0 and snap()['checkpoint']==-1 and snap()['health']==spec['player']['health'],snap())
                else:
                    page.wait_for_timeout(180)
            record('win_condition',snap()['state']=='won',{'method':'Controlled collection and gate overlaps through all stages, not an autonomous completion','snapshot':snap()})
            if len(levels)>1:
                record('level_transitions',len(transitions)==len(levels)-1 and snap()['state']=='won',{'transitions':transitions,'method':'Real exit collision, scene transition and final-stage win'},'fidelity')
            generation=snap()['generation']
            press('r')
            page.wait_for_function('(n)=>window.__AETHER_PLATFORMER__?.snapshot().generation>n',arg=generation,timeout=4000)
            record('restart_after_victory',snap()['levelIndex']==0 and snap()['crystals']==0 and snap()['checkpoint']==-1 and snap()['state']=='playing',snap())
            restart()
            hazard=next((e for e in spec['entities'] if e['kind'] in ('spikes','enemy')),None)
            if hazard:
                teleport(hazard['x'],hazard['y']);page.wait_for_timeout(180)
                record('hazard_damage',snap()['health']<spec['player']['health'],{'method':'Controlled overlap with real hazard or enemy','snapshot':snap()})
            restart(len(levels)-1)
            for _ in range(spec['player']['health']):page.evaluate('window.__AETHER_PLATFORMER__.damage()')
            record('loss_condition',snap()['state']=='lost' and snap()['levelIndex']==len(levels)-1,{'method':'Test hook invokes damage on final level to exercise health exhaustion','snapshot':snap()})
            generation=snap()['generation'];press('r')
            page.wait_for_function('(n)=>window.__AETHER_PLATFORMER__?.snapshot().generation>n',arg=generation,timeout=4000)
            wait_grounded();reset=snap()
            record('restart_reset',reset['levelIndex']==0 and reset['health']==spec['player']['health'] and reset['crystals']==0 and reset['checkpoint']==-1 and reset['state']=='playing',reset)
            page.screenshot(path=str(directory/'gameplay.png'),full_page=True)
            record('no_runtime_exceptions',not errors,errors,'runtime')
        except Exception as exc:
            try: failure_state=page.evaluate('window.__AETHER_PLATFORMER__?.snapshot() || null')
            except Exception: failure_state=None
            record('browser_execution',False,{'error':type(exc).__name__+': '+str(exc)[:500],'snapshot':failure_state},'runtime')
            page.screenshot(path=str(directory/'failure.png'),full_page=True)
        finally:
            browser.close()
    return finish_report()


if __name__=='__main__':
    import sys
    report=run_browser_qa(sys.argv[1],Path(sys.argv[2]),json.loads(Path(sys.argv[3]).read_text(encoding='utf-8')) if len(sys.argv)>3 else None);print(json.dumps(report));sys.exit(0 if report['overall']=='PASS' else 1)
