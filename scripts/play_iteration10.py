"""Real-time finite survival and real-keyboard runner trajectories.

Adventure uses disclosed evasion teleports. Runners use no state overrides.
"""
import sys,json,time,math
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/iteration10'

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    results=[]
    for case in ['easy','runner']:
        spec=json.loads((OUT/case/'spec.json').read_text());page.route('**/fixtures/*.json',lambda route:route.fulfill(json=spec))
        page.goto('http://127.0.0.1:5173/studio?example=forest');page.wait_for_function('window.__runner');page.locator('canvas').click();page.keyboard.press('r')
        start=time.monotonic();jumped=0
        while time.monotonic()-start<12:
            state=page.evaluate('''()=>{const w=window.__runner.world;return {state:w.state,distance:w.distance,speed:w.speed,y:w.y,vy:w.vy,score:w.score,next:w.obstacles.find(o=>o.x+o.width>w.distance+166)}}''')
            if state['state']!='playing':break
            o=state.get('next')
            if o and state['y']>=429.9 and state['vy']==0:
                h=0 if o['kind']=='gap' else o.get('height',40)
                root=math.sqrt(max(0,spec['jump_impulse']**2-2*spec['gravity']*(h+4)))
                entry=(spec['jump_impulse']-root)/spec['gravity'];exit=(spec['jump_impulse']+root)/spec['gravity']
                target=state['speed']*(entry+(exit-entry-(o['width']+28)/state['speed'])/2)
                if o['x']-(state['distance']+194)<=target:
                    page.keyboard.press('Space');jumped+=1
            page.wait_for_timeout(16)
        result={'case':case,'duration':round(time.monotonic()-start,2),'jumps':jumped,'final':state,'passed':state['state']=='playing' and time.monotonic()-start>=12,'method':'Actual Space/R inputs, reading live obstacles for jump timing; no state overrides'}
        results.append(result);print(json.dumps(result),flush=True);page.screenshot(path=str(OUT/case/'keyboard-play.png'),full_page=True);page.unroute('**/fixtures/*.json')
    spec=json.loads((OUT/'laboratory/spec.json').read_text());page.route('**/fixtures/*.json',lambda route:route.fulfill(json=spec))
    page.goto('http://127.0.0.1:5173/studio?example=forest&test=1');page.wait_for_function('window.__AETHER_ADVENTURE__?.snapshot().ready');page.locator('.game-surface').click()
    candidates=[(x*32+16,y*32+16) for y in range(2,30) for x in range(2,46) if all(spec['areas'][0]['tiles'][y+dy][x+dx] not in (1,4) for dx in (-1,0,1) for dy in (-1,0,1))]
    start=time.monotonic()
    while time.monotonic()-start<75:
        state=page.evaluate('window.__AETHER_ADVENTURE__.snapshot()')
        if state['won'] or state['lost']:break
        if state['actors']:
            dest=max(candidates,key=lambda p:min((p[0]-a['x'])**2+(p[1]-a['y'])**2 for a in state['actors']))
            page.evaluate('([x,y])=>window.__AETHER_ADVENTURE__.teleport(x,y)',dest)
        page.wait_for_timeout(100)
    score=state['score'];page.wait_for_timeout(300)
    stopped=page.evaluate('window.__AETHER_ADVENTURE__.snapshot().score')==score
    page.screenshot(path=str(OUT/'laboratory/sixty-second-victory.png'),full_page=True)
    generation=state['generation'];page.keyboard.press('r');page.wait_for_function('(g)=>window.__AETHER_ADVENTURE__.snapshot().generation>g',arg=generation,timeout=4000)
    result={'case':'laboratory-60-seconds','wall_seconds':round(time.monotonic()-start,2),'score':score,'won':state['won'],'lost':state['lost'],'score_stopped':stopped,'restart':page.evaluate('window.__AETHER_ADVENTURE__.snapshot().score')<.3,'passed':state['won'] and not state['lost'] and 60<=score<60.1 and stopped,'method':'Actual elapsed 60-second scheduler, unchanged health and attack clocks; controlled evasion teleports only'}
    results.append(result);print(json.dumps(result),flush=True)
    (OUT/'play-results.json').write_text(json.dumps({'results':results,'page_errors':errors},indent=2),encoding='utf-8');browser.close()
