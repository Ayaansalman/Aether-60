"""Verify survival sample and actual live game in the creator; no model calls."""
import json,re
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path('docs/evidence/survival-fix/creator');out.mkdir(exist_ok=True)
checks=[];errors=[]
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True);p=b.new_page(viewport={'width':1440,'height':1000});p.on('pageerror',lambda e:errors.append(str(e)))
 p.goto('http://localhost:5173/studio');p.get_by_role('button',name=re.compile('Bulletfall Survival')).click()
 # Sample runtime is production mode; real controls and rendered UI prove the adapter loads without QA hooks.
 p.locator('canvas').wait_for();checks.append({'id':'sample_button','passed':'Bulletfall Survival' in p.locator('body').inner_text() and 'Offline example' in p.locator('body').inner_text()})
 p.goto('http://localhost:5173/studio/play/4d8ceb5c-1f91-424d-9f75-f052de60707b?test=1');p.wait_for_function('window.__survivalScene&&window.__AETHER_GAME__?.ready');p.locator('.game-surface').click()
 checks.append({'id':'live_preview','passed':p.evaluate("window.__survivalScene.gameIR.genre==='arena_survival'&&window.__AETHER_GAME__.getState().maxHp===3")})
 p.get_by_role('button',name='Design',exact=True).click();checks.append({'id':'survival_blueprint','passed':'Shooters fire 5 shots at 1s intervals' in p.locator('.design-view').inner_text()})
 p.get_by_role('button',name='Game preview',exact=True).click();p.locator('.game-surface').click();p.wait_for_function('window.__AETHER_GAME__?.ready');p.evaluate('window.__AETHER_GAME__.pauseEnemies(true)');p.screenshot(path=str(out/'desktop.png'),full_page=True)
 p.set_viewport_size({'width':390,'height':844});button=p.get_by_role('button',name='Game right',exact=True);button.scroll_into_view_if_needed();box=button.bounding_box();before=p.evaluate('window.__AETHER_GAME__.getState().player.x');p.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);p.mouse.down();p.wait_for_timeout(250);p.mouse.up();after=p.evaluate('window.__AETHER_GAME__.getState().player.x')
 checks.append({'id':'mobile_direction_input','passed':after>before+20,'before':before,'after':after});checks.append({'id':'mobile_health_readable','passed':p.locator('.adventure-mobile-status').is_visible() and '3/3 health' in p.locator('.adventure-mobile-status').inner_text()})
 p.screenshot(path=str(out/'mobile.png'),full_page=True);checks.append({'id':'no_runtime_errors','passed':not errors,'errors':errors});b.close()
r={'overall':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':checks};(out/'report.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(r)
