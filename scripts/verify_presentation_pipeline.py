"""Fixture HTTP jobs through real construction/Chromium QA, with public preview gating."""
import json,time,sys
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/presentation-ready'
OUT.mkdir(parents=True,exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
cases=[
    ('runner','Create an easy automatic forest runner with obstacles and distance scoring.'),
    ('platformer','Create a peaceful easy forest platformer with no enemies, no hazards and checkpoints.'),
    ('adventure','Create a peaceful top-down woodland village adventure. Collect three magical herbs for a healer and return them. No combat.'),
    ('boss','Create a platformer boss duel in a stone castle. Exactly one boss with charge and projectile attacks, no collectibles. Defeat the boss to win.'),
    ('survival','Create a top-down laboratory survival game. Survive for 60 seconds with three health, chasers and shooters firing projectile volleys. Score survival time.'),
]
results=[]
with httpx.Client(base_url='http://127.0.0.1:8001',timeout=30) as client,sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1100})
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    for name,prompt in cases:
        response=client.post('/api/v2/games',json={'prompt':prompt,'mode':'fixture','seed':7})
        response.raise_for_status();gid=response.json()['game_id']
        page.goto(f'http://127.0.0.1:5174/studio/play/{gid}')
        states=[];blocked=True;observed=False;deadline=time.monotonic()+250
        while time.monotonic()<deadline:
            data=client.get('/api/v2/games/'+gid).json();status=data['job']['status']
            if not states or states[-1]!=status:states.append(status)
            if status in ('READY','READY_WITH_WARNINGS','FAILED'):break
            if status=='TESTING':
                observed=True
                blocked=blocked and page.locator('canvas').count()==0
            page.wait_for_timeout(400)
        qa=data['artifacts'].get('qa_report.json',{})
        playable=False
        if qa.get('overall')=='PASS' and status in ('READY','READY_WITH_WARNINGS'):
            page.locator('canvas').wait_for(timeout=20000);playable=True
        result=dict(case=name,game_id=gid,status=status,qa=qa.get('overall'),
            checks=len(qa.get('checks',[])),failed=[c['id'] for c in qa.get('checks',[]) if not c['passed']],
            observed_testing=observed,public_canvas_held_during_qa=blocked,
            public_game_playable=playable,public_url_preserved='/studio/play/' in (data['job'].get('game_url') or ''),
            stages=states,page_errors=list(errors))
        results.append(result)
        page.screenshot(path=str(OUT/(name+'-pipeline.png')),full_page=True)
        (OUT/'pipeline.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(json.dumps(result))
    browser.close()
assert all(r['qa']=='PASS' and r['public_game_playable'] and r['public_canvas_held_during_qa'] and r['public_url_preserved'] and not r['page_errors'] for r in results),results
