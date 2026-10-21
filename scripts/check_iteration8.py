"""Fixture-backed Chromium checks, followed by real key control with read-only telemetry.
No model calls. Prior functional QA discloses its own controlled collision/score state.
"""
import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from services.runner_qa import run_browser_qa
from playwright.sync_api import sync_playwright
out=ROOT/'docs/evidence/iteration8'
keys=sys.argv[1:] or list('ABCD')
for key in keys:
    directory=out/key;spec=json.loads((directory/'spec.json').read_text())
    report=run_browser_qa('http://localhost:5173/studio?example=forest',directory,spec)
    print(key,'functional',report['overall'],[(c['id'],c['details']) for c in report['checks'] if not c['passed']],flush=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
        page.route('**/fixtures/*.json',lambda r:r.fulfill(json=spec))
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://localhost:5173/studio?example=forest');page.wait_for_function('window.__runner');page.locator('canvas').click();page.keyboard.press('r')
        last=-1;start=time.monotonic();samples=[]
        while time.monotonic()-start<12:
            data=page.evaluate('''()=>{const w=window.__runner.world;return {state:w.state,distance:w.distance,score:w.score,best:w.best,y:w.y,vy:w.vy,speed:w.speed,elapsed:w.elapsed,impulse:w.spec.jump_impulse,gravity:w.spec.gravity,obstacle:w.obstacles.find(o=>o.x+o.width>w.distance+166)}}''')
            if data['state']!='playing':break
            o=data.get('obstacle');px=data['distance']+180
            if o:
                if spec['mode']=='ground':
                    if o['id']!=last and o['x']+o['width']/2-px<=data['speed']*spec['jump_impulse']/spec['gravity']:
                        page.keyboard.press('Space');last=o['id']
                elif data['y']>o['center']+5 and data['vy']>0:page.keyboard.press('Space')
            samples.append({k:data[k] for k in ['distance','score','y','speed']})
            page.wait_for_timeout(25)
        page.locator('canvas').screenshot(path=str(directory/'controlled-play.png'))
        final=page.evaluate('window.__runner.snapshot()')
        assets=page.evaluate('''()=>[...performance.getEntriesByType('resource')].filter(r=>r.name.includes('/assets/platformer/')).map(r=>r.name.split('/').pop())''')
        play={'seconds':time.monotonic()-start,'final':final,'errors':errors,'assets_loaded':assets,'samples':samples[::20],'scope':'Real Space keyboard events selected from read-only world telemetry; no position, collision or velocity overrides. Scripted controller, not human enjoyment testing.'}
        (directory/'controlled-play.json').write_text(json.dumps(play,indent=2),encoding='utf-8')
        print(key,'keyboard play',final,flush=True)
        browser.close()
