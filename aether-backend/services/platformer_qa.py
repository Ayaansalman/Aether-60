"""Real browser evidence. Controlled state injection is explicitly identified per check."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run_browser_qa(url: str, directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    checks, errors, failed_assets = [], [], []
    def record(name, passed, detail, category="gameplay", critical=True):
        checks.append({"id":name,"passed":bool(passed),"critical":critical,"category":category,"details":detail})
        (directory/'qa_progress.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width":1440,"height":1000}, device_scale_factor=1)
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
            def restart():
                generation=snap()['generation']
                page.evaluate('window.__AETHER_PLATFORMER__.restart()')
                page.wait_for_function('(n)=>window.__AETHER_PLATFORMER__?.snapshot().ready && window.__AETHER_PLATFORMER__.snapshot().generation>n',arg=generation,timeout=4000)
                wait_grounded()
            if '/studio/play/' in url:
                gid=url.split('/studio/play/')[1].split('?')[0]
                spec=page.evaluate('(id)=>fetch(`/api/v2/games/${id}/spec`).then(r=>r.json())',gid)
            else:
                from urllib.parse import parse_qs,urlparse
                name=parse_qs(urlparse(url).query).get('example',['forest'])[0]
                spec=page.evaluate('(name)=>fetch(`/fixtures/${name}.json`).then(r=>r.json())',name)
            page.locator('canvas').click()
            page.wait_for_timeout(400)
            record('canvas_and_assets',not snap()['missingAssets'] and not failed_assets,{'missing':snap()['missingAssets'],'http_failures':failed_assets},'runtime')
            before=snap();page.keyboard.down('ArrowRight');page.wait_for_timeout(280);page.keyboard.up('ArrowRight');after=snap()
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
            # Exercise every mandatory edge with actual keyboard and gravity.
            # Isolated launch positioning prevents earlier damage from masking later edge defects.
            route=[p for p in spec['platforms'] if not p['moving']]
            edge_results=[]
            for a,b in zip(route,route[1:]):
                restart()
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
                platform_index=spec['platforms'].index(b)
                # Optional moving routes can catch a jump above the destination's static floor.
                # Accept only a settled, physically observed landing on that section's registered route.
                surfaces=[p['y']*36 for p in spec['platforms'] if p['moving'] and b['x']<=p['x']<b['x']+b['width']]
                target_info={'index':platform_index,'left':b['x']*36,'right':(b['x']+b['width'])*36,'surfaces':surfaces}
                predicate='''(t)=>{const s=window.__AETHER_PLATFORMER__.snapshot();return s.landedPlatforms.includes(t.index)||(s.state==='playing'&&s.grounded&&s.x>t.left&&s.x<t.right&&t.surfaces.some(y=>Math.abs(s.y+24-y)<8));}'''
                try:page.wait_for_function(predicate,arg=target_info,timeout=4000)
                except Exception:pass
                result=snap()
                settled_alternate=result['state']=='playing' and result['grounded'] and target_info['left']<result['x']<target_info['right'] and any(abs(result['y']+24-y)<8 for y in surfaces)
                edge_results.append({'from':a['x'],'to':b['x'],'landed':platform_index in result['landedPlatforms'] or settled_alternate,'route':'moving alternate' if settled_alternate else 'static floor','snapshot':result})
            record('mandatory_route_edges',all(e['landed'] for e in edge_results),{'method':'Isolated launch positions; actual keyboard jumps, physics and landing for each destination section, including registered moving alternates. This is not a full autonomous playthrough.','edges':edge_results},'level_layout')
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
            if spec['objective']['required']:
                teleport(gate['x'],gate['y']);page.wait_for_timeout(80)
                record('locked_exit',snap()['state']=='playing',{'method':'Controlled exit overlap without required crystals','snapshot':snap()})
            for entity in spec['entities']:
                if entity['kind']=='crystal':
                    teleport(entity['x'],entity['y']);page.wait_for_timeout(30)
            teleport(gate['x'],gate['y']);page.wait_for_timeout(150)
            record('win_condition',snap()['state']=='won',{'method':'Controlled collection and gate overlaps, not an autonomous completion','snapshot':snap()})
            restart()
            hazard=next((e for e in spec['entities'] if e['kind'] in ('spikes','enemy')),None)
            if hazard:
                teleport(hazard['x'],hazard['y']);page.wait_for_timeout(180)
                record('hazard_damage',snap()['health']<spec['player']['health'],{'method':'Controlled overlap with real hazard or enemy','snapshot':snap()})
            for _ in range(spec['player']['health']):page.evaluate('window.__AETHER_PLATFORMER__.damage()')
            record('loss_condition',snap()['state']=='lost',{'method':'Test hook invokes damage to exercise health exhaustion','snapshot':snap()})
            restart();reset=snap()
            record('restart_reset',reset['health']==spec['player']['health'] and reset['crystals']==0 and reset['checkpoint']==-1 and reset['state']=='playing',reset)
            page.screenshot(path=str(directory/'gameplay.png'),full_page=True)
            record('no_runtime_exceptions',not errors,errors,'runtime')
        except Exception as exc:
            record('browser_execution',False,type(exc).__name__+': '+str(exc)[:500],'runtime')
            page.screenshot(path=str(directory/'failure.png'),full_page=True)
        finally:
            browser.close()
    report = {'overall':'PASS' if checks and all(c['passed'] for c in checks if c['critical']) else 'FAIL','checks':checks,
        'page_errors':errors,'screenshot':'gameplay.png','scope':'Functional browser verification; visual coherence and game quality require screenshot/play review.'}
    (directory/'qa_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    import sys
    report=run_browser_qa(sys.argv[1],Path(sys.argv[2]));print(json.dumps(report));sys.exit(0 if report['overall']=='PASS' else 1)
