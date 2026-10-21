"""Real browser checks. Controlled placement is disclosed; gameplay events use real inputs/physics."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def run_browser_qa(url, directory, fixture=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[];assets=[]
    def record(id,passed,details):
        checks.append({'id':id,'passed':bool(passed),'critical':True,'category':'adventure','details':details})
        (directory/'qa_progress.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        if fixture is not None:page.route('**/fixtures/*.json',lambda route:route.fulfill(json=fixture))
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:assets.append(r.url) if r.status>=400 and '/assets/' in r.url else None)
        snap=lambda:page.evaluate('window.__AETHER_ADVENTURE__.snapshot()')
        def teleport(x,y):page.evaluate('([x,y])=>window.__AETHER_ADVENTURE__.teleport(x,y)',[x,y])
        def press(key,ms=75):
            page.keyboard.down(key);page.wait_for_timeout(ms);page.keyboard.up(key);page.wait_for_timeout(40)
        def close_dialogue():
            for _ in range(6):
                if not snap()['dialogue']:break
                press('e')
        def restart():
            generation=snap()['generation'];press('r')
            page.wait_for_function('(g)=>window.__AETHER_ADVENTURE__.snapshot().generation>g',arg=generation)
        try:
            page.goto(url+('&' if '?' in url else '?')+'test=1',wait_until='domcontentloaded')
            page.wait_for_function('window.__AETHER_ADVENTURE__?.snapshot().ready',timeout=25000)
            if fixture is not None:spec=fixture
            elif '/studio/play/' in url:
                gid=url.split('/studio/play/')[1].split('?')[0]
                spec=page.evaluate('(id)=>fetch(`/api/v2/games/${id}/spec`).then(r=>r.json())',gid)
            else:
                from urllib.parse import parse_qs,urlparse
                name=parse_qs(urlparse(url).query)['example'][0]
                spec=page.evaluate('(n)=>fetch(`/fixtures/${n}.json`).then(r=>r.json())',name)
            page.locator('.game-surface').click()
            record('genre_assets_gravity',snap()['genre']=='adventure' and snap()['gravity']==0 and not snap()['missingAssets'] and not assets,{'snapshot':snap(),'asset_http_failures':assets})
            area=spec['areas'][0]
            page.wait_for_timeout(500)
            page.screenshot(path=str(directory/'opening.png'),full_page=True)
            before=snap();press('ArrowRight',220);after=snap()
            record('top_down_horizontal_movement',after['x']>before['x']+20,{'before':before['x'],'after':after['x']})
            # Find a broad clear 3x3 destination, then verify upward movement with zero gravity.
            clear=next((x,y) for y in range(2,area['height']-2) for x in range(2,area['width']-2)
                       if all(area['tiles'][y+dy][x+dx] not in (1,4) and area['tiles'][y+dy][x+dx]<10 for dy in (-1,0,1) for dx in (-1,0,1)))
            teleport(clear[0]*32+16,clear[1]*32+16);before=snap();press('ArrowUp',170);after=snap()
            record('top_down_vertical_movement',before['y']-after['y']>15 and after['gravity']==0,{'before_y':before['y'],'after_y':after['y']})
            if spec.get('art'):
                frames=[];teleport(clear[0]*32+16,clear[1]*32+16);page.keyboard.down('ArrowRight')
                for _ in range(7):
                    page.wait_for_timeout(70);frames.append(snap()['playerFrame'])
                page.keyboard.up('ArrowRight')
                record('registered_animation_frames',len(set(frames))>1,{'observed_frames':frames,'asset':spec['art']['player']})
                directions=[]
                for key,direction in [('ArrowLeft','left'),('ArrowUp','up'),('ArrowDown','down')]:
                    press(key);directions.append(snap().get('animation',''))
                record('directional_art_and_pack',snap()['assetPack']==spec['art']['pack_id'] and all(direction in animation for direction,animation in zip(['left','up','down'],directions)),{'directions':directions,'selected_assets':snap()['selectedAssets']})
            # Controlled placement next to a real solid terrain tile, then real keyboard collision.
            boundary=None
            for y in range(1,area['height']-1):
                for x in range(1,area['width']-1):
                    if area['tiles'][y][x] in (1,4) or area['tiles'][y][x]>=10:continue
                    for dx,dy,key in [(1,0,'ArrowRight'),(-1,0,'ArrowLeft'),(0,1,'ArrowDown'),(0,-1,'ArrowUp')]:
                        if area['tiles'][y+dy][x+dx] in (1,4) or area['tiles'][y+dy][x+dx]>=10:
                            boundary=(x,y,dx,dy,key);break
                    if boundary:break
                if boundary:break
            x,y,dx,dy,key=boundary;teleport(x*32+16,y*32+16);press(key,450);after=snap()
            record('environment_collision',abs(after['x']-(x*32+16))<26 and abs(after['y']-(y*32+16))<26,{'adjacent_wall':boundary,'after':[after['x'],after['y']]})
            restart()
            if spec['combat']:
                enemy=next((a for a in snap()['actors'] if a['kind']=='enemy'),None)
                if enemy:
                    teleport(enemy['x']-105,enemy['y']);before=snap();page.wait_for_timeout(350);after=snap()
                    moved=next((a for a in after['actors'] if a['id']==enemy['id']),None)
                    record('enemy_movement',moved and abs(moved['x']-enemy['x'])+abs(moved['y']-enemy['y'])>4,{'before':enemy,'after':moved})
                    for _ in range(7):
                        enemy=next(a for a in snap()['actors'] if a['kind']=='enemy')
                        teleport(enemy['x'],enemy['y']);page.wait_for_timeout(1050)
                        if snap()['lost']:break
                    record('combat_health_loss',snap()['lost'] and snap()['health']==0,snap())
                    restart();record('restart_after_loss',not snap()['lost'] and snap()['health']==5,snap())
                # Demonstrate the seal refuses opening before keys/switches exist.
                door=next((a for a in area['actors'] if a['kind']=='door' and a['requires']),None)
                if door:
                    teleport(door['x']*32-18,door['y']*32+16);press('e')
                    record('locked_door_requires_resources',door['id'] not in snap()['unlocked'] and bool(snap()['dialogue']),snap())
                    close_dialogue()
            for index,goal in enumerate(spec['quests']):
                target=next(a for a in spec['areas'][snap()['area']]['actors'] if a['id']==goal['target'])
                x,y=target['x']*32+16,target['y']*32+16
                if goal['kind']=='collect' and target['kind']=='item':
                    for point in target['pickups']:
                        teleport(point['x']*32+16,point['y']*32+16);page.wait_for_timeout(140)
                    page.wait_for_timeout(450)
                    page.screenshot(path=str(directory/f'collection-{index}.png'),full_page=True)
                    record(f'inventory_{index}',snap()['inventory'].get(target['item'],0)>=goal['count'],snap()['inventory'])
                elif goal['kind']=='defeat':
                    for _ in range(10):
                        enemy=next((a for a in snap()['actors'] if a['id']==target['id']),None)
                        if not enemy:break
                        teleport(enemy['x']-60,enemy['y']);press('ArrowRight',25);press('f');page.wait_for_timeout(380)
                    record(f'combat_{target["id"]}',not any(a['id']==target['id'] for a in snap()['actors']),snap())
                else:
                    if goal['kind']=='unlock':
                        teleport(x-40,y);press('ArrowRight',420)
                        record('sealed_passage_collision',snap()['x']<x-14,snap())
                    teleport(x-33,y);press('e')
                    if goal['kind'] in ('talk','deliver'):
                        record(f'dialogue_{index}',bool(snap()['dialogue']),snap()['dialogue'])
                        page.screenshot(path=str(directory/f'dialogue-{index}.png'),full_page=True)
                    close_dialogue()
                    if goal['kind']=='unlock':
                        press('ArrowRight',520)
                        record('unlocked_passage_traversal',snap()['x']>x+20,snap())
                    if goal['kind']=='deliver':
                        delivered=goal.get('delivery_items') or {goal['item']:goal['count']}
                        record('inventory_delivery_consumed',all(snap()['inventory'].get(item,0)==0 for item in delivered),snap()['inventory'])
                record(f'quest_{index}_{goal["kind"]}',snap()['quests'][index]=='COMPLETED',snap())
                next_goal=spec['quests'][index+1] if index+1<len(spec['quests']) else None
                next_area=next((i for i,ar in enumerate(spec['areas']) if next_goal and any(a['id']==next_goal['target'] for a in ar['actors'])),snap()['area'])
                if next_area>snap()['area']:
                    old=snap()['area'];exit=spec['areas'][old]['exit'];teleport(exit['x']*32+16,exit['y']*32+16);press('e')
                    page.wait_for_function('(a)=>window.__AETHER_ADVENTURE__.snapshot().area>a',arg=old,timeout=4000)
                    record('area_transition',snap()['area']==next_area,snap())
            exit=spec['areas'][snap()['area']]['exit'];teleport(exit['x']*32+16,exit['y']*32+16);press('e')
            record('adventure_completion',snap()['won'] and all(s=='COMPLETED' for s in snap()['quests']),snap())
            page.screenshot(path=str(directory/'completed.png'),full_page=True)
            restart();record('whole_game_restart',snap()['area']==0 and not snap()['won'] and not snap()['inventory'] and snap()['quests'][0]=='ACTIVE',snap())
            page.screenshot(path=str(directory/'gameplay.png'),full_page=True)
            record('no_runtime_exceptions',not errors,errors)
        except Exception as exc:
            record('browser_execution',False,{'error':str(exc)[:700],'page_errors':errors})
            page.screenshot(path=str(directory/'failure.png'),full_page=True)
        finally:browser.close()
    report={'overall':'PASS' if checks and all(c['passed'] for c in checks) else 'FAIL','checks':checks,'page_errors':errors,
            'scope':'Controlled placement, real keyboard movement/collision/interactions/projectiles. Not autonomous navigation or arbitrary prompt fidelity certification.'}
    (directory/'qa_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    import sys
    report=run_browser_qa(sys.argv[1],Path(sys.argv[2]))
    print(json.dumps(report));sys.exit(0 if report['overall']=='PASS' else 1)
