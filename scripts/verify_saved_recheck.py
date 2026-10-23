"""Recheck an existing local job and verify public release; no model requests."""
import json,sys,time
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

gid=sys.argv[1];out=Path(__file__).resolve().parents[1]/'docs/evidence/qa-recheck-fix'
out.mkdir(parents=True,exist_ok=True)
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=15) as api,sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:5173/studio/play/{gid}?test=1')
    page.wait_for_function('window.__AETHER_ADVENTURE__?.snapshot().ready')
    initial=page.locator('canvas').count()==1 and page.get_by_test_id('generation-outcome').count()==0
    # Start through the actual Studio action, which also resumes polling after
    # the saved job's previous terminal state.
    page.get_by_role('button',name='Inspector',exact=True).click()
    with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith(f'/api/v2/games/{gid}/verify')) as request:
        page.get_by_role('button',name='Recheck game',exact=True).click()
    assert request.value.status==202
    page.get_by_test_id('generation-progress').wait_for()
    observed=False;held=True;deadline=time.monotonic()+240
    while time.monotonic()<deadline:
        data=api.get(f'/api/v2/games/{gid}').json();status=data['job']['status']
        if status in ('READY','READY_WITH_WARNINGS','FAILED'):break
        if status=='TESTING':observed=True;held=held and page.locator('canvas').count()==0
        page.wait_for_timeout(500)
    page.wait_for_function('window.__AETHER_ADVENTURE__?.snapshot().ready')
    page.locator('canvas').click();before=page.evaluate('window.__AETHER_ADVENTURE__.snapshot().x')
    page.keyboard.down('ArrowRight');page.wait_for_timeout(220);page.keyboard.up('ArrowRight')
    moved=page.evaluate('window.__AETHER_ADVENTURE__.snapshot().x')>before+10
    artifacts=data['artifacts']
    latest=max((n for n in artifacts if n.startswith('qa_retest_')),key=lambda n:int(n.split('_')[-1].split('.')[0]))
    result={'game_id':gid,'historical_recheck_opens':initial,'status':status,'observed_testing':observed,
        'public_canvas_held_during_qa':held,'current_qa':artifacts['qa_report.json']['overall'],
        'latest_retest':latest,'latest_retest_matches_current':artifacts[latest]==artifacts['qa_report.json'],
        'original_qa_preserved':artifacts['qa_report_initial.json']['overall'],
        'qa_checks':len(artifacts['qa_report.json']['checks']),'real_keyboard_movement':moved,
        'no_stale_failure_panel':page.get_by_test_id('generation-outcome').count()==0,
        'terminal_event':data['events'][-1]['stage'],'page_errors':errors}
    page.screenshot(path=str(out/'last-stand-recovered.png'),full_page=True);browser.close()
    (out/'browser-recovery.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
    assert initial and moved and held and observed and result['current_qa']=='PASS' and result['latest_retest_matches_current'] and result['no_stale_failure_panel'] and result['terminal_event']==status and not errors,result
