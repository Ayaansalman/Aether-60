import json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright

def run_browser_qa(url,directory,fixture=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
    def record(id,ok,details):
        checks.append({'id':id,'passed':bool(ok),'critical':True,'details':details})
        (directory/'qa_progress.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000})
        if fixture:page.route('**/fixtures/*.json',lambda r:r.fulfill(json=fixture))
        page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(url+('&' if '?' in url else '?')+'test=1');page.wait_for_function('window.__survivalScene&&window.__AETHER_GAME__?.ready',timeout=25000)
            page.locator('.game-surface').click()
            spec=page.evaluate('window.__survivalScene.gameIR')
            state=lambda:page.evaluate('window.__AETHER_GAME__.getState()')
            page.evaluate('window.__AETHER_GAME__.pauseEnemies(true)');before=state();page.keyboard.down('ArrowRight');page.wait_for_timeout(220);page.keyboard.up('ArrowRight');after=state()
            record('survival_movement',after['player']['x']>before['player']['x']+20 and after['maxHp']==spec['player']['max_health'],[before,after])
            record('no_quest_template',spec['objective']['type'].startswith('survive_') and not spec['collectibles'] and spec['player']['attack_mode']=='avoid_only',{'objective':spec['objective'],'collectibles':spec['collectibles']})
            # Seeded controlled spawn-clock advancement, keeping the actual constructor and role sampler.
            page.evaluate('''()=>{const s=window.__survivalScene;s.enemies.clear(true,true);s.enemiesPaused=false;for(let i=0;i<30;i++){s.streamNextAt=-1;s.update(s.time.now,0);}s.enemiesPaused=true;}''')
            trace=page.evaluate('window.__survivalScene.streamTrace');roles={r['type'] for r in trace};record('random_enemy_spawns',len(trace)>2 and len({(r['x'],r['y']) for r in trace})==len(trace) and all(((r['x']-after['player']['x'])**2+(r['y']-after['player']['y'])**2)**.5>=spec['survival_stream']['safe_radius']-2 for r in trace),trace)
            record('enemy_chaser','chaser' in roles,sorted(roles));record('enemy_shooter','shooter' in roles,sorted(roles))
            # Isolate one shooter, use real Phaser time for first two intervals, then accelerate its clock.
            page.evaluate('''()=>{const s=window.__survivalScene;s.enemies.clear(true,true);s.streamNextAt=s.time.now+1e9;s.respawnEnemy('shooter',0,{x:80,y:110});s.enemiesPaused=false;s.player.setPosition(850,440);s.streamShots=0;s.streamExpired=0;}''')
            interval=spec['survival_stream']['shot_interval_ms'];page.wait_for_timeout(max(50,interval-180));early=page.evaluate('window.__survivalScene.streamShots')
            page.wait_for_function('window.__survivalScene.streamShots>=1',timeout=interval+3000);shot1=page.evaluate('window.__survivalScene.streamShots');page.wait_for_timeout(120);still=page.evaluate('window.__survivalScene.streamShots')
            if spec['survival_stream']['shooter_shots']>1:
                page.wait_for_function('window.__survivalScene.streamShots>=2',timeout=interval+3000)
                times=page.evaluate('window.__survivalScene.streamFires.slice(-2)');spacing=times[-1]['at']-times[-2]['at']
            else:spacing=interval
            record('shot_interval',early==0 and shot1==1 and still==1 and spacing>=interval,{'before_interval':early,'after_interval':shot1,'after_120ms':still,'measured_spacing_ms':spacing,'required_interval_ms':interval})
            result=page.evaluate('''()=>{const s=window.__survivalScene,e=s.enemies.getChildren()[0],config=s.gameIR.survival_stream;const initial=s.streamShots;for(let i=initial;i<config.shooter_shots;i++){e.setData('lastShootTime',s.time.now-config.shot_interval_ms);s.update(s.time.now,0);}return {shots:s.streamShots,expired:s.streamExpired,active:s.enemies.getLength(),bullets:s.enemyProjectilesGroup.getLength()}}''')
            record('emitter_lifecycle',result['shots']==spec['survival_stream']['shooter_shots'] and result['expired']==1 and result['active']==0 and result['bullets']>0,result)
            # Put a genuine enemy projectile on the player body for a collision-driven health decrease.
            before=state()['hp'];page.evaluate('''()=>{const s=window.__survivalScene;s.isInvulnerable=false;const b=s.enemyProjectilesGroup.getChildren()[0];b.setPosition(s.player.x,s.player.y);b.body.reset(s.player.x,s.player.y);b.body.setVelocity(0,0);}''');page.wait_for_timeout(150)
            record('survival_damage',state()['hp']==before-1,{'before':before,'after':state()['hp']})
            hits=[{'before':before,'after':state()['hp']}]
            for _ in range(state()['hp']):
                hp=state()['hp']
                page.evaluate('''()=>{const s=window.__survivalScene;s.isInvulnerable=false;s.shootEnemyBullet(s.player);const bullets=s.enemyProjectilesGroup.getChildren(),b=bullets[bullets.length-1];b.setPosition(s.player.x,s.player.y);b.body.reset(s.player.x,s.player.y);b.body.setVelocity(0,0);}''')
                page.wait_for_timeout(100);hits.append({'before':hp,'after':state()['hp']})
            record('survival_loss',state()['status']=='lost' and state()['hp']==0 and all(h['before']-h['after']==1 for h in hits),{'collision_hits':hits,'state':state()})
            page.keyboard.down('r');page.wait_for_timeout(100);page.keyboard.up('r');page.wait_for_function("window.__AETHER_GAME__?.getState().status==='playing'",timeout=4000)
            record('survival_restart',state()['hp']==spec['player']['max_health'] and state()['timeElapsed']<=1 and page.evaluate('window.__survivalScene.streamShots')==0,state())
            page.evaluate('window.__AETHER_GAME__.pauseEnemies(true)');page.evaluate('window.__AETHER_GAME__.advanceTimer(240)')
            if spec['objective']['type']=='survive_endless':record('endless_survival',state()['status']=='playing' and state()['timeElapsed']>=240,state())
            record('survival_score',state()['timeElapsed']>=240,state())
            bounded=page.evaluate('''()=>{const s=window.__survivalScene;s.enemiesPaused=false;for(let i=0;i<200;i++){s.streamNextAt=-1;s.update(s.time.now,0);}return {active:s.enemies.getLength(),trace:s.streamTrace.length,max:s.gameIR.survival_stream.max_active}}''')
            record('bounded_stream',bounded['active']<=bounded['max'] and bounded['trace']<=64,bounded)
            page.evaluate('window.__AETHER_GAME__.pauseEnemies(true)');page.screenshot(path=str(directory/'gameplay.png'),full_page=True);record('no_runtime_exceptions',not errors,errors)
        except Exception as exc:
            record('browser_execution',False,{'error':str(exc)[:1000],'errors':errors});page.screenshot(path=str(directory/'failure.png'),full_page=True)
        finally:browser.close()
    report={'overall':'PASS' if checks and all(c['passed'] for c in checks) else 'FAIL','checks':checks,'scope':'Real keyboard/Phaser movement, two real firing intervals, controlled spawn/emitter clocks and projectile positioning; not autonomous survival.'}
    (directory/'qa_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
if __name__=='__main__':print(json.dumps(run_browser_qa(sys.argv[1],sys.argv[2])))
