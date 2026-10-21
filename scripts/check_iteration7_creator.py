"""Actual creator submission, Inspector, controls and mobile tap; offline mode, zero model calls."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from tests.test_iteration7 import C
from playwright.sync_api import sync_playwright
out=ROOT/'docs/evidence/iteration7/creator';out.mkdir(parents=True,exist_ok=True)
checks=[];errors=[]
def record(id,ok,detail):checks.append({'id':id,'passed':bool(ok),'details':detail})
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000},has_touch=True)
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://localhost:5173/studio');page.locator('textarea').fill(C);page.locator('select').first.select_option('fixture')
 with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/api/v2/games')) as response:page.get_by_role('button',name='Generate game',exact=True).click()
 gid=response.value.json()['game_id']
 for _ in range(70):
  result=page.request.get('http://localhost:8000/api/v2/games/'+gid).json()
  if result['job']['status'] in ['READY','READY_WITH_WARNINGS','FAILED']:break
  page.wait_for_timeout(1000)
 page.wait_for_function('window.__runner');page.wait_for_timeout(1200)
 record('creator_runner_generation',result['job']['status']=='READY' and result['artifacts']['game_ir_v2.json']['genre']=='runner',{'game_id':gid,'status':result['job']['status']})
 controls=page.locator('.game-controls').inner_text();record('runner_control_labels','Automatic scrolling' in controls and 'Move' not in controls,controls)
 page.get_by_role('button',name='Inspector',exact=True).click();page.locator('#artifact-select').select_option('semantic_requirement_report.json');record('semantic_inspector','control_preserved' in page.locator('.inspector-panel pre').inner_text(),page.locator('.inspector-panel pre').inner_text())
 page.screenshot(path=str(out/'desktop.png'),full_page=True)
 page.get_by_role('button',name='Close inspector').click();page.set_viewport_size({'width':390,'height':844});page.locator('canvas').scroll_into_view_if_needed();page.locator('canvas').tap();page.keyboard.press('r');page.locator('canvas').tap()
 record('mobile_tap_jump',page.evaluate('window.__runner.world.vy')<0,page.evaluate('window.__runner.snapshot()'));page.screenshot(path=str(out/'mobile.png'),full_page=True)
 record('no_browser_errors',not errors,errors);browser.close()
report={'overall':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':checks,'scope':'Actual creator UI submits deterministic scenario C through API and uses current runner runtime, Inspector and mobile pointer input; no model calls.'}
(out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');(out/'job.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(report)
