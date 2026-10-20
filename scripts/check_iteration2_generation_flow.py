"""Actual creator submission and configured timer regression; no mocked backend progress."""
import json
import shutil
import time
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'docs/evidence/iteration2/timer-flow'
PROMPT='Create a frozen underground platformer with falling icicles every 1.5 seconds and a flashing light at the exit.'

if __name__=='__main__':
    DEST.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as w, httpx.Client(timeout=15) as client:
        browser=w.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:5173/studio?example=ice&test=1')
        page.wait_for_function('window.__AETHER_PLATFORMER__?.snapshot().ready')
        page.evaluate('window.previousCanvas=document.querySelector("canvas")')
        page.locator('#game-prompt').fill(PROMPT)
        page.locator('#provider-mode').select_option('fixture')
        with page.expect_response(lambda r:r.url.endswith('/api/v2/games') and r.request.method=='POST') as response:
            page.get_by_role('button',name='Generate game',exact=True).click()
        gid=response.value.json()['game_id']
        assert page.evaluate('!window.previousCanvas.isConnected'), 'Previous sample was not cleared'
        assert page.get_by_role('button',name='Building your world…').is_disabled()
        page.screenshot(path=str(DEST/'generating.png'),full_page=True)
        page.get_by_role('button',name='Inspector',exact=True).click()
        stages=[];last=None;deadline=time.monotonic()+270
        while time.monotonic()<deadline:
            data=client.get('http://127.0.0.1:8000/api/v2/games/'+gid).json()
            status=data['job']['status']
            if status!=last:
                stages.append(status);last=status;print(status,flush=True)
            if status in ('READY','READY_WITH_WARNINGS','FAILED'):break
            page.wait_for_timeout(1000)
        (DEST/'job.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        assert status=='READY', (status,data['job'].get('error_code'))
        qa=data['artifacts']['qa_report.json'];assert qa['overall']=='PASS'
        traps=[e for e in data['artifacts']['game_ir_v2.json']['entities'] if e['kind']=='icicle']
        assert traps and all(e['trigger']=='timer' and e['period_ms']==1500 for e in traps)
        assert not errors, errors
        page.get_by_role('button',name='Close inspector',exact=True).click()
        page.get_by_role('button',name='Generate game',exact=True).wait_for()
        page.screenshot(path=str(DEST/'ready.png'),full_page=True)
        result={'game_id':gid,'source':'Actual creator UI submission, explicit offline fixture; real backend and browser QA',
                'observed_stages':stages,'event_stages':[e['stage'] for e in data['events']],
                'previous_sample_cleared':True,'timer_ms':1500,'qa':qa['overall'],'page_errors':errors}
        (DEST/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        source=ROOT/'aether-backend/artifacts'/gid
        for path in source.rglob('*.png'):
            target=DEST/'qa'/path.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        print(json.dumps(result,indent=2));browser.close()
