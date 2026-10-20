"""Real creator control checks. --game-id also checks export and restart on a saved job."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:5173')
    parser.add_argument('--game-id')
    args=parser.parse_args()
    evidence=Path(__file__).resolve().parents[1]/'docs/evidence/iteration2/ui'
    evidence.mkdir(parents=True,exist_ok=True)
    results=[]
    with sync_playwright() as w:
        browser=w.chromium.launch(headless=True)
        for width,height,name in [(1440,1000,'desktop'),(390,844,'mobile')]:
            p=browser.new_page(viewport={'width':width,'height':height})
            errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
            p.goto(args.url+'/studio?test=1',wait_until='domcontentloaded')
            p.get_by_role('heading',name='Your next world belongs here.').wait_for()
            results.append({'id':name+'_empty','passed':p.locator('canvas').count()==0 and p.locator('#game-prompt').input_value()==''})
            p.screenshot(path=str(evidence/(name+'-empty.png')),full_page=True)
            p.locator('#game-prompt').fill('A quiet forest with crystals')
            p.keyboard.type(' and space')
            results.append({'id':name+'_typing','passed':p.locator('#game-prompt').input_value().endswith(' and space')})
            p.get_by_role('button',name='Design',exact=True).click()
            results.append({'id':name+'_design','passed':p.get_by_role('heading',name='World blueprint').is_visible()})
            p.get_by_role('button',name='Game preview',exact=True).click()
            p.get_by_role('button',name='Inspector',exact=True).click()
            results.append({'id':name+'_honest_inspector','passed':p.get_by_text('No generation has run yet.').is_visible()})
            p.get_by_role('button',name='Close inspector',exact=True).click()
            results.append({'id':name+'_overflow','passed':p.evaluate('document.documentElement.scrollWidth<=innerWidth')})
            if width==390:
                results.append({'id':'mobile_document_scroll','passed':p.evaluate('getComputedStyle(document.body).overflowY==="visible" && document.body.clientHeight>=document.querySelector("#root").clientHeight')})
            p.route('**/api/v2/games',lambda route:route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'Seeded UI test: generation service unavailable. Retry generation.'})))
            p.get_by_role('button',name='Generate game',exact=True).click()
            p.get_by_role('alert').wait_for()
            results.append({'id':name+'_error_recovery','passed':p.locator('canvas').count()==0 and p.get_by_role('button',name='Generate game',exact=True).is_enabled(),
                            'method':'Intentionally seeded 503 response; real UI error/recovery state, no backend/provider result claimed'})
            p.screenshot(path=str(evidence/(name+'-error.png')),full_page=True)
            p.unroute('**/api/v2/games')
            if width==390:
                p.get_by_role('button',name='The Verdant Passage Sample').click()
                p.wait_for_function('window.__AETHER_PLATFORMER__?.snapshot().ready')
                button=p.get_by_role('button',name='Game right',exact=True)
                button.scroll_into_view_if_needed()
                p.wait_for_function('window.__AETHER_PLATFORMER__?.snapshot().ready')
                before=p.evaluate('window.__AETHER_PLATFORMER__.snapshot().x')
                button.dispatch_event('pointerdown',{'pointerId':1});p.wait_for_timeout(280);button.dispatch_event('pointerup',{'pointerId':1})
                results.append({'id':'touch_move','passed':p.evaluate('window.__AETHER_PLATFORMER__.snapshot().x')>before+15})
            results.append({'id':name+'_exceptions','passed':not errors,'errors':errors})
            p.screenshot(path=str(evidence/(name+'-studio.png')),full_page=True)
            p.close()
        if args.game_id:
            p=browser.new_page(viewport={'width':1440,'height':1000})
            p.goto(args.url+'/studio/play/'+args.game_id+'?test=1',wait_until='domcontentloaded')
            p.wait_for_function('window.__AETHER_PLATFORMER__?.snapshot().ready')
            p.locator('canvas').click();p.evaluate('window.__AETHER_PLATFORMER__.damage()')
            p.keyboard.down('r');p.wait_for_timeout(85);p.keyboard.up('r')
            p.wait_for_function('window.__AETHER_PLATFORMER__?.snapshot().health===3')
            results.append({'id':'keyboard_restart','passed':True})
            p.get_by_role('button',name='Expand game',exact=True).click()
            p.wait_for_selector('.expanded-preview')
            results.append({'id':'expand_preview','passed':p.get_by_role('button',name='Exit expanded game').is_visible()})
            p.keyboard.press('Escape');p.wait_for_selector('.expanded-preview',state='detached')
            p.get_by_role('button',name='Inspector',exact=True).click()
            button=p.get_by_role('button',name='Export engineering evidence');button.scroll_into_view_if_needed()
            with p.expect_download() as download:button.click()
            data=json.loads(Path(download.value.path()).read_text())
            results.append({'id':'export_evidence','passed':data['job']['game_id']==args.game_id and 'repair_report.json' in data['artifacts']})
            p.get_by_role('button',name='Close inspector',exact=True).click()
            p.evaluate('window.oldCanvas=document.querySelector("canvas")')
            p.get_by_role('button',name='Restart game',exact=True).click()
            p.wait_for_function('document.querySelector("canvas")!==window.oldCanvas && window.__AETHER_PLATFORMER__?.snapshot().ready')
            results.append({'id':'toolbar_restart','passed':True})
        browser.close()
    (evidence/'ui-checks-final.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
    raise SystemExit(0 if all(r['passed'] for r in results) else 1)


if __name__=='__main__':main()
