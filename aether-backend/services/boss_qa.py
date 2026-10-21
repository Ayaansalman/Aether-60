import json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright

def run_browser_qa(url,directory,fixture=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
    def record(id,ok,details):checks.append({'id':id,'passed':bool(ok),'critical':True,'details':details})
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1400,'height':1000})
        if fixture:page.route('**/fixtures/*.json',lambda r:r.fulfill(json=fixture))
        page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(url+('&' if '?' in url else '?')+'test=1');page.wait_for_function('window.__AETHER_PLATFORMER__?.snapshot().ready',timeout=25000);page.locator('.game-surface').click()
            # QA-only access to encounter internals permits isolated collision checks.
            page.wait_for_function('window.__bossScene?.hero?.body',timeout=5000)
            page.wait_for_timeout(600)
            init=page.evaluate('''()=>{const s=window.__bossScene;return {count:s.enemies.length,health:s.enemies[0].health,bar:!!s.children.getByName('boss-health'),entities:s.spec.entities.length}}''')
            record('boss_arena',init['count']==1 and init['entities']==1 and init['health']>=4 and init['bar'],init)
            # Advance only the attack clock, observe runtime telegraph and actual projectiles.
            patterns=page.evaluate('''()=>{const s=window.__bossScene,e=s.enemies[0];e.memory={phase:'windup',at:s.time.now-1000,direction:-1,cycle:2};return true}''');page.wait_for_timeout(60)
            record('boss_volley',page.evaluate('window.__bossScene.shotsFired')>0,patterns)
            page.evaluate('''()=>{const s=window.__bossScene,e=s.enemies[0];e.memory={phase:'windup',at:s.time.now-1000,direction:-1,cycle:1};}''');page.wait_for_timeout(60)
            record('boss_charge',abs(page.evaluate('window.__bossScene.enemies[0].sprite.body.velocity.x'))>=260,'Controlled attack clock, real runtime charge')
            # Isolate boss at a known projectile lane and use the real player attack input.
            page.evaluate('''()=>{const s=window.__bossScene,e=s.enemies[0];s.projectiles.clear(true,true);s.hurtAt=s.time.now+60000;s.hero.setPosition(240,470);e.sprite.setPosition(500,470);e.sprite.setVelocity(0);e.memory={phase:'recover',at:s.time.now+60000,direction:-1};s.facing=1;}''');page.wait_for_timeout(500);page.keyboard.down('f');page.wait_for_timeout(90);page.keyboard.up('f');page.wait_for_function('(hp)=>window.__bossScene.enemies[0].health<hp',arg=init['health'],timeout=4000)
            health=page.evaluate('window.__bossScene.enemies[0].health');record('player_attack_damage',health<init['health'],{'before':init['health'],'after':health,'snapshot':page.evaluate('window.__bossScene.snapshot()')})
            page.evaluate('''()=>{const s=window.__bossScene,e=s.enemies[0];s.hurtAt=-10000;e.memory.phase='recover';s.hero.setPosition(e.sprite.x,e.sprite.y+12);s.hero.setVelocityY(0);}''');page.wait_for_timeout(100)
            record('boss_player_damage',page.evaluate('window.__bossScene.health')<5,'Controlled overlap, real collision damage')
            page.evaluate('''()=>{const s=window.__bossScene,e=s.enemies[0];e.health=1;e.memory.phase='recover';s.hero.setPosition(240,470);e.sprite.setPosition(500,470);s.facing=1;}''');page.wait_for_timeout(250);page.keyboard.down('f');page.wait_for_timeout(90);page.keyboard.up('f');page.wait_for_function("window.__bossScene.state==='won'",timeout=4000)
            record('boss_duel',page.evaluate("window.__bossScene.state==='won'"),'Final health set to one; real projectile collision triggers victory without exit')
            page.screenshot(path=str(directory/'completed.png'),full_page=True)
            page.keyboard.down('r');page.wait_for_timeout(90);page.keyboard.up('r');page.wait_for_timeout(500);record('boss_restart',page.evaluate("window.__bossScene.state==='playing'&&window.__bossScene.enemies[0].health>=4"),'Real R restart')
            page.screenshot(path=str(directory/'gameplay.png'),full_page=True);record('no_runtime_exceptions',not errors,errors)
        except Exception as e:record('browser_execution',False,str(e)[:900])
        finally:browser.close()
    report={'overall':'PASS' if checks and all(c['passed'] for c in checks) else 'FAIL','checks':checks,'scope':'Controlled positions, boss clock and final HP; real Phaser collisions, projectiles and keyboard. Not an autonomous duel.'}
    (directory/'qa_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
if __name__=='__main__':print(json.dumps(run_browser_qa(sys.argv[1],sys.argv[2])))
