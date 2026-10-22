import json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright

def run_browser_qa(url,directory,fixture=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
    def record(id,ok,details): checks.append({'id':id,'passed':bool(ok),'critical':True,'details':details})
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1400,'height':1000})
        if fixture:page.route('**/fixtures/*.json',lambda r:r.fulfill(json=fixture))
        page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(url);page.wait_for_function('window.__runner',timeout=25000)
            page.locator('canvas').click();page.keyboard.press('r')
            before=page.evaluate('window.__runner.snapshot()');page.keyboard.press('Space');page.wait_for_timeout(100)
            after=page.evaluate('window.__runner.snapshot()');record('runner_input',after['vy']<0 and after['distance']>before['distance'],[before,after])
            if after['mode']=='flap':
                page.keyboard.press('Space');record('repeatable_flap',page.evaluate('window.__runner.world.vy')<0, 'Real keyboard airborne flap')
                page.locator('canvas').dispatch_event('pointerdown');record('pointer_flap',page.evaluate('window.__runner.world.vy')<0,'Pointer event applies impulse')
            result=page.evaluate('''()=>{const w=window.__runner.world;w.restart();w.obstacles=[];w.nextX=1e9;w.y=10;w.step(1/120);return window.__runner.snapshot()}''')
            record('bounds_death',result['state']=='lost',result)
            page.keyboard.press('Space');result=page.evaluate('window.__runner.snapshot()');record('rapid_restart',result['state']=='playing' and result['distance']<80 and result['score']<=8 and result['generation']>before['generation'],result)
            page.evaluate('window.__oldRunner=window.__runner.world')
            page.get_by_role('button',name='Restart game',exact=True).click()
            page.wait_for_function('window.__runner.world!==window.__oldRunner')
            focused=page.evaluate("document.activeElement?.tagName==='CANVAS'")
            page.keyboard.press('Space');page.wait_for_timeout(40)
            record('toolbar_restart_focus',focused and page.evaluate('window.__runner.world.vy<0'),'Actual toolbar remount restores canvas focus and real Space input')
            field=page.locator('textarea').first
            probe=not field.count() or not field.is_enabled()
            if probe:
                # The actual prompt is disabled while production QA is running.
                # Exercise the same native editable focus with a temporary field.
                page.evaluate("()=>{const field=document.createElement('textarea');field.id='qa-typing-probe';document.body.append(field);field.focus();}")
            else:field.focus()
            generation=page.evaluate('window.__runner.world.generation');page.keyboard.press('r')
            record('typing_isolation',page.evaluate('window.__runner.world.generation')==generation,{'method':'Real R in a focused native textarea; temporary field only when the creator prompt is disabled during generation','temporary_field':probe})
            if probe:page.evaluate("document.getElementById('qa-typing-probe').remove()")
            page.locator('canvas').click()
            page.evaluate('document.activeElement.blur()');generation=page.evaluate('window.__runner.world.generation');page.keyboard.press('r')
            record('body_focus_restart',page.evaluate('window.__runner.world.generation')>generation,'After engagement, R recovers from canvas focus loss to the page body')
            score=page.evaluate('''()=>{const w=window.__runner.world;w.restart();w.obstacles=[{id:999,x:100,width:30,kind:'gate',center:250,gap:240,passed:false}];w.y=250;w.step(1/120);const a=w.score;w.step(1/120);if(w.spec.mode==='ground'){w.obstacles=[];w.nextX=1e9;for(let i=0;i<120;i++)w.step(1/120);return [w.score,Math.floor(w.distance/10)];}return [a,w.score]}''')
            record('score_once',score==[1,1] if after['mode']=='flap' else score[0]>0 and score[0]==score[1],score)
            collision=page.evaluate('''()=>{const w=window.__runner.world;w.restart();w.obstacles=[{id:999,x:170,width:60,kind:w.spec.mode==='flap'?'gate':'laser',center:420,gap:175,passed:false}];w.step(1/120);return w.state}''');record('obstacle_collision',collision=='lost',collision)
            progression=page.evaluate('''()=>{const w=window.__runner.world;w.restart();for(let i=0;i<10000;i++){w.distance+=100;w.populate();w.obstacles=w.obstacles.filter(o=>o.x+o.width>w.distance-100);}const serial=w.serial;w.populate();return {active:w.obstacles.length,serial:w.serial,endless:w.spec.endless,stopped:w.serial===serial,pending:w.stream.pending.length}}''')
            record('endless_bounded_state' if progression['endless'] else 'finite_stream_bounds',(progression['serial']>500 if progression['endless'] else progression['serial']>0 and progression['stopped']) and progression['active']<12 and progression['pending']<=8,progression)
            page.keyboard.press('r');page.screenshot(path=str(directory/'gameplay.png'),full_page=True)
            record('no_runtime_exceptions',not errors,errors)
        except Exception as e:record('browser_execution',False,str(e)[:900])
        finally:browser.close()
    report={'overall':'PASS' if checks and all(c['passed'] for c in checks) else 'FAIL','checks':checks,'scope':'Real keyboard/pointer input plus disclosed controlled state for collision/scoring and accelerated generation; not autonomous survival.'}
    (directory/'qa_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
if __name__=='__main__':print(json.dumps(run_browser_qa(sys.argv[1],sys.argv[2])))
