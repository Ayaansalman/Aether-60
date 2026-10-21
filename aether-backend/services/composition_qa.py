"""Chromium checks for typed top-down behavior composition in AdventureScene."""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def run_browser_qa(url,directory,fixture=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[]
    def record(id,passed,details):checks.append({'id':id,'passed':bool(passed),'critical':True,'category':'composition','details':details})
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000})
        if fixture is not None:page.route('**/fixtures/*.json',lambda route:route.fulfill(json=fixture))
        page.on('pageerror',lambda e:errors.append(str(e)))
        snap=lambda:page.evaluate('window.__AETHER_ADVENTURE__.snapshot()')
        def teleport(x,y):page.evaluate('([x,y])=>window.__AETHER_ADVENTURE__.teleport(x,y)',[x,y])
        def restart():
            generation=snap()['generation'];page.keyboard.press('r')
            page.wait_for_function('(g)=>window.__AETHER_ADVENTURE__.snapshot().generation>g',arg=generation)
        try:
            page.goto(url+('&' if '?' in url else '?')+'test=1',wait_until='domcontentloaded')
            page.wait_for_function('window.__AETHER_ADVENTURE__?.snapshot().ready',timeout=25000)
            page.locator('.game-surface').click()
            spec=fixture
            if spec is None:
                gid=url.split('/studio/play/')[1].split('?')[0]
                spec=page.evaluate('(id)=>fetch(`/api/v2/games/${id}/spec`).then(r=>r.json())',gid)
            config=spec['gameplay'];area=spec['areas'][0]
            record('composition_contract',snap()['health']==config['health'] and not snap()['questMode'] and not snap()['inventory'] and not snap()['quests'] and not snap()['missingAssets'],snap())
            before=snap();page.keyboard.down('ArrowRight');page.wait_for_timeout(200);page.keyboard.up('ArrowRight');after=snap()
            record('top_down_horizontal_movement',after['x']>before['x']+15 and after['gravity']==0,{'before':before['x'],'after':after['x']})
            # Real scheduling and enemy AI. Controlled player repositioning avoids death while observing complete sequences.
            # Safe, clear tiles are also used as evade destinations; no timers, counters or health are modified.
            candidates=[(x*32+16,y*32+16) for y in range(2,area['height']-2) for x in range(2,area['width']-2)
                if all(area['tiles'][y+dy][x+dx] not in (1,4) and area['tiles'][y+dy][x+dx]<10 for dy in (-1,0,1) for dx in (-1,0,1))]
            events={};observed_roles=set();positions={};pursued=False;attack_anim=False
            max_spawn=max(s['interval_ms'] for s in config['spawns'])
            max_attack=max((a['attack']['windup_ms']+(a['attack']['shots']-1)*a['attack']['interval_ms'] for a in config['archetypes'] if a.get('attack')),default=0)
            deadline=time.monotonic()+min(28,(max_spawn*4+max_attack)/1000+3)
            while time.monotonic()<deadline:
                state=snap()
                for event in state['behavior']['events']:events[(event['type'],event['id'],event['at'])]=event
                for a in state['actors']:
                    observed_roles.add(a['role']);attack_anim|='attack' in (a.get('animation') or '')
                    if a['id'] in positions and a['role'] in {r['id'] for r in config['archetypes'] if r['behavior']=='chase'}:
                        old=positions[a['id']];pursued|=abs(old[0]-a['x'])+abs(old[1]-a['y'])>3
                    positions[a['id']]=(a['x'],a['y'])
                if state['lost']:break
                if state['actors']:
                    dest=max(candidates,key=lambda p:min((p[0]-a['x'])**2+(p[1]-a['y'])**2 for a in state['actors']))
                    teleport(*dest)
                page.wait_for_timeout(100)
            state=snap();spawned=[e for e in events.values() if e['type']=='spawn']
            record('composition_safe_spawning',len(spawned)>=2 and all(e['distance']>=min(s['safe_radius'] for s in config['spawns']) for e in spawned),{'spawns':spawned,'world_validation':validate_world_from_spec(spec)})
            record('composition_enemy_roles',observed_roles=={a['id'] for a in config['archetypes']} and pursued,{'roles':sorted(observed_roles),'chaser_moved':pursued})
            completed=[]
            for event in events.values():
                if event['type']!='despawn':continue
                fired=sorted([e for e in events.values() if e['type']=='shot' and e['id']==event['id']],key=lambda e:e['at'])
                if fired:completed.append(fired)
            attacks=[a['attack'] for a in config['archetypes'] if a.get('attack') and a['attack']['after']=='despawn']
            matched=any(len(seq)==a['shots'] and all(abs(y['at']-x['at']-a['interval_ms'])<.01 for x,y in zip(seq,seq[1:])) for seq in completed for a in attacks)
            record('composition_attack_sequence',matched,{'completed_sequences':completed,'expected':attacks,'method':'Real-time scheduler; player teleports to evade. No attack clocks/counters changed.'})
            record('composition_feedback',state['feedback'].get('windup',0)>0 and state['feedback'].get('defeat',0)>0,{'events':state['feedback'],'asset_attack_animation_observed':attack_anim})
            record('composition_survival_score',state['score']>2 and abs(state['score']-state['behavior']['elapsed']/1000)<.001,state['score'])
            page.screenshot(path=str(directory/'gameplay.png'),full_page=True)
            # Observe an actual emitted projectile and use controlled overlap to verify its damage.
            deadline=time.monotonic()+8;projectile_damage=False
            while time.monotonic()<deadline and not snap()['lost']:
                state=snap()
                if state['projectiles']:
                    bullet=state['projectiles'][0];old_health=state['health'];teleport(bullet['x'],bullet['y']);page.wait_for_timeout(80)
                    if snap()['health']<old_health:projectile_damage=True;break
                page.wait_for_timeout(50)
            record('composition_projectile_damage',projectile_damage,{'method':'Controlled player overlap with actual emitted projectile', 'snapshot':snap()})
            # Force actual collision by repositioning the player onto a live enemy, one invulnerability window apart.
            for _ in range(config['health']+3):
                state=snap()
                if state['lost']:break
                enemy=next((a for a in state['actors'] if a['kind']=='enemy'),None)
                if enemy:teleport(enemy['x'],enemy['y'])
                page.wait_for_timeout(config['invulnerability_ms']+100)
            lost=snap();record('composition_health_loss',lost['lost'] and lost['health']==0,lost)
            score=lost['score'];page.wait_for_timeout(350)
            record('composition_score_stops',snap()['score']==score,{'at_loss':score,'later':snap()['score']})
            restart();state=snap()
            record('whole_game_restart',state['health']==config['health'] and not state['lost'] and not state['won'] and state['behavior']['totalShots']==0 and state['score']<.2,state)
            record('no_runtime_exceptions',not errors,errors)
        except Exception as exc:
            record('browser_execution',False,{'error':str(exc)[:700],'page_errors':errors})
            page.screenshot(path=str(directory/'failure.png'),full_page=True)
        finally:browser.close()
    report={'overall':'PASS' if checks and all(c['passed'] for c in checks) else 'FAIL','checks':checks,'page_errors':errors,
        'scope':'Actual Phaser timers/AI/projectiles and collision. Controlled player repositioning for evasion and damage; not autonomous full playthrough or subjective quality assessment.'}
    (directory/'qa_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


def validate_world_from_spec(spec):
    from schemas.adventure import AdventureIR
    from services.adventure import validate_world
    return validate_world(AdventureIR.model_validate(spec))['overall']


if __name__=='__main__':
    import sys
    report=run_browser_qa(sys.argv[1],Path(sys.argv[2]));print(json.dumps(report));sys.exit(0 if report['overall']=='PASS' else 1)
