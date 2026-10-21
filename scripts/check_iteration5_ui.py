"""Targeted creator integration. One real offline submission, no provider call."""
import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'aether-backend'))
from tests.test_adventure import VILLAGE

if __name__=='__main__':
    base=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:5174'
    directory=Path(os.getenv('AETHER_UI_EVIDENCE_DIR',str(ROOT/'docs/evidence/iteration5/creator')));directory.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[]
    def record(id,passed):checks.append({'id':id,'passed':bool(passed)})
    with sync_playwright() as pw:
        browser=pw.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        if len(sys.argv)>2:
            gid=sys.argv[2];page.goto(base+'/studio/play/'+gid+'?test=1')
        else:
            page.goto(base+'/studio?test=1');page.locator('#provider-mode').select_option('fixture');page.locator('#game-prompt').fill(VILLAGE)
            with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/api/v2/games')) as accepted:
                page.get_by_role('button',name='Generate game').click()
            gid=accepted.value.json()['game_id']
            (directory/'submission.json').write_text(json.dumps({'game_id':gid,'mode':'fixture','source':'Actual creator form submission'}))
        page.wait_for_function('window.__AETHER_ADVENTURE__?.snapshot().ready',timeout=45000)
        page.wait_for_function('!document.querySelector(".generate-button").disabled',timeout=120000)
        record('prompt_routes_to_adventure',page.evaluate('window.__AETHER_ADVENTURE__.snapshot().genre')=='adventure')
        page.get_by_role('button',name='Design',exact=True).click()
        record('adventure_blueprint',page.locator('.design-view').inner_text().find('magical herbs')>=0)
        page.get_by_role('button',name='Game preview',exact=True).click()
        page.locator('.inspector-button').click();page.locator('#artifact-select').select_option('game_ir_v2.json')
        record('inspector_real_adventure_ir','"genre": "adventure"' in page.locator('.inspector-content pre').inner_text())
        page.screenshot(path=str(directory/'inspector.png'),full_page=True);page.get_by_role('button',name='Close inspector').click()
        x=page.evaluate('window.__AETHER_ADVENTURE__.snapshot().x');page.locator('#game-prompt').focus();page.keyboard.type(' wasd e f')
        record('typing_does_not_control_game',page.evaluate('window.__AETHER_ADVENTURE__.snapshot().x')==x)
        page.evaluate('window.__AETHER_ADVENTURE__.teleport(400,432)');page.get_by_role('button',name='Restart game',exact=True).click()
        page.wait_for_function('window.__AETHER_ADVENTURE__?.snapshot().x===112')
        record('toolbar_restart',page.evaluate('window.__AETHER_ADVENTURE__.snapshot().quests[0]')=='ACTIVE')
        page.get_by_role('button',name='Expand game',exact=True).click();record('expanded_preview',page.get_by_role('dialog',name='Expanded game preview').is_visible())
        page.keyboard.press('Escape');record('escape_closes_expanded',page.get_by_role('dialog',name='Expanded game preview').count()==0)
        page.screenshot(path=str(directory/'desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        button=page.get_by_role('button',name='Game right',exact=True);button.scroll_into_view_if_needed();box=button.bounding_box()
        before=page.evaluate('window.__AETHER_ADVENTURE__.snapshot().x');page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);page.mouse.down();page.wait_for_timeout(300);page.mouse.up()
        record('mobile_touch_movement',page.evaluate('window.__AETHER_ADVENTURE__.snapshot().x')>before+20)
        record('mobile_readable_objective',page.locator('.adventure-mobile-status').is_visible() and 'Talk to the healer' in page.locator('.adventure-mobile-status').inner_text())
        page.evaluate('(()=>{const h=window.__AETHER_ADVENTURE__,n=h.snapshot().actors.find(a=>a.id==="guide");h.teleport(n.x-33,n.y);})()')
        talk=page.get_by_role('button',name='Game interact',exact=True);talk.scroll_into_view_if_needed();box=talk.bounding_box()
        page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);page.mouse.down();page.wait_for_timeout(100);page.mouse.up()
        record('mobile_readable_dialogue',page.locator('.adventure-mobile-status p').is_visible() and bool(page.evaluate('window.__AETHER_ADVENTURE__.snapshot().dialogue.length')))
        record('mobile_no_horizontal_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
        page.screenshot(path=str(directory/'mobile.png'),full_page=True)
        record('no_runtime_exceptions',not errors);browser.close()
    report={'overall':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':checks,'page_errors':errors,'game_id':gid,'source':'Actual creator submission in explicit fixture mode; no language model call'}
    (directory/'qa_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report));sys.exit(0 if report['overall']=='PASS' else 1)
