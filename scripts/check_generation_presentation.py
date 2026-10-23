"""Real Studio rendering/input with controlled job responses; no model calls."""
import json,re,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/presentation-ready/ui';OUT.mkdir(parents=True,exist_ok=True)
spec=json.loads((ROOT/'aether-frontend/public/fixtures/auto-runner.json').read_text(encoding='utf-8'))
payload={};disconnect=False;checks=[];errors=[];posts=[]
sys.stdout.reconfigure(encoding='utf-8')

def event(id,stage,detail,result='START'):return dict(id=id,stage=stage,detail=detail,result=result,ts='2026-10-22T08:00:00Z',rationale='Controlled presentation regression')
def set_job(status,events,qa=None,semantic=None):
    payload.clear();payload.update(job=dict(game_id='ui-demo',prompt='Create an easy automatic forest runner',status=status,model_id='backup-model',limitations=['Environmental animation is limited.'] if status=='READY_WITH_WARNINGS' else []),events=events,artifacts={'game_ir_v2.json':spec})
    if qa:payload['artifacts']['qa_report.json']=qa
    if semantic:payload['artifacts']['semantic_requirement_report.json']=semantic
def record(name,passed,detail):
    checks.append(dict(id=name,passed=bool(passed),details=detail))
    (OUT/'report.json').write_text(json.dumps(dict(checks=checks,page_errors=errors),indent=2),encoding='utf-8')
    assert passed,name

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1100})
    page.on('pageerror',lambda error:errors.append(str(error)))
    def route(request):
        if request.request.method=='POST':
            posts.append(request.request.post_data_json)
            request.fulfill(json={'game_id':'ui-demo','status':'QUEUED'});return
        if disconnect:request.abort();return
        request.fulfill(json=payload)
    page.route(re.compile(r'/api/v2/games(?:/|$)'),route)
    events=[event(1,'QUEUED','Accepted request'),event(2,'PLANNING','Interpreting central loop, controls and constraints')]
    set_job('PLANNING',events)
    page.goto('http://127.0.0.1:5173/studio/play/ui-demo')
    try:page.get_by_text('Understanding your request',exact=True).wait_for(timeout=10000)
    except Exception:
        print(page.locator('body').inner_text());print(errors);raise
    record('intent_progress_no_canvas',page.locator('canvas').count()==0 and page.get_by_text('Understanding your request',exact=True).is_visible(),'Actual Studio DOM, even though an IR is already present')
    events+= [event(3,'MODEL_FALLBACK','primary-model → backup-model: quota or rate limit. Continuing the same request.'),event(4,'SELECTING_ASSETS','Selecting licensed artwork'),event(5,'BUILDING','Preparing game runtime'),event(6,'TESTING','Running real Chromium checks')]
    set_job('TESTING',events)
    page.get_by_text('Running gameplay QA',exact=True).wait_for()
    record('qa_pending_no_canvas',page.locator('canvas').count()==0,'Public preview remains unmounted throughout TESTING')
    record('fallback_visible',page.get_by_text('API model fallback',exact=True).is_visible(),'Recorded model transition appears below the frame')
    page.screenshot(path=str(OUT/'qa-pending.png'),full_page=True)
    set_job('REPAIRING',events+[event(7,'REPAIRING','Reducing an unreachable gap; rebuilding the same design')])
    page.get_by_text('Repairing and rechecking',exact=True).wait_for()
    record('repair_keeps_game_hidden',page.locator('canvas').count()==0,'Repair progress from backend events')
    set_job('READY_WITH_WARNINGS',events+[event(8,'READY_WITH_WARNINGS','Browser checks passed','SUCCESS')],{'overall':'PASS','checks':[]},{'overall':'WARN','requirements':[]})
    page.wait_for_function('window.__runner')
    record('qa_pass_unlocks_play',page.locator('canvas').count()==1 and page.get_by_text('Environmental animation is limited.',exact=True).is_visible(),'READY_WITH_WARNINGS plus QA PASS mounts the runtime and retains limitations')
    page.screenshot(path=str(OUT/'ready.png'),full_page=True)

    set_job('FAILED',events+[event(9,'FAILED','The final gate is missing one required switch.','FAILED')],{'overall':'FAIL','checks':[{'id':'shared_gate_dependency','passed':False}]},{'overall':'FAIL','requirements':[{'source':'Both switches must open the gate','status':'failed'}]})
    page.reload();page.get_by_test_id('generation-outcome').wait_for()
    record('failure_under_canvas',page.locator('canvas').count()==0 and 'missing one required switch' in page.get_by_test_id('generation-outcome').inner_text(),'Specific failure and invariant are displayed below the held preview')
    page.screenshot(path=str(OUT/'failed.png'),full_page=True)

    set_job('READY_WITH_WARNINGS',events,{'overall':'UNAVAILABLE','checks':[]})
    page.reload();page.get_by_text('Gameplay verification is incomplete',exact=True).first.wait_for()
    record('unavailable_qa_is_blocked',page.locator('canvas').count()==0 and page.get_by_role('button',name='Run QA again',exact=True).is_enabled(),'Terminal warning status alone cannot unlock play')

    set_job('TESTING',events)
    page.reload();page.get_by_test_id('generation-progress').wait_for();disconnect=True
    page.get_by_role('button',name='Reconnect',exact=True).wait_for()
    disconnect=False;set_job('READY',events,{'overall':'PASS','checks':[]})
    page.get_by_role('button',name='Reconnect',exact=True).click();page.wait_for_function('window.__runner')
    record('reconnect_without_regeneration',not posts and page.locator('canvas').count()==1,'Reconnect polls the same saved job and makes no generation POST')

    set_job('TESTING',events)
    page.goto('http://127.0.0.1:5173/studio/verify/ui-demo');page.wait_for_function('window.__runner')
    record('qa_route_runs_before_public_ready',page.locator('canvas').count()==1,'Dedicated backend verification route mounts the same runtime during TESTING')
    page.goto('http://127.0.0.1:5173/studio?example=auto-runner');page.wait_for_function('window.__runner')
    record('offline_samples_preserved',page.locator('canvas').count()==1,'Existing saved examples still play immediately')

    page.set_viewport_size({'width':390,'height':844});page.goto('http://127.0.0.1:5173/studio/play/ui-demo');page.get_by_test_id('generation-progress').wait_for()
    record('mobile_progress_fits',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1') and page.locator('canvas').count()==0,'390px viewport, no horizontal overflow')
    page.screenshot(path=str(OUT/'mobile-progress.png'),full_page=True)
    record('no_runtime_exceptions',not errors,errors)
    browser.close()
print(json.dumps({'passed':len(checks),'checks':checks,'page_errors':errors}))
