"""Focused browser probes for registered components and objective-driven campaigns.

Positions are controlled; activation, projectiles, stomps, physics, goals and scene
transitions are real. These probes do not claim autonomous completion or enjoyment.
"""


def uses_components(spec):
    return bool(spec.get('campaign_goals') or any(level.get('goals') or level.get('links') or level.get('player_attack')=='projectile' or
                any(e.get('behavior') in ('turret','ambusher') and e['kind']=='enemy' for e in level['entities'])
                for level in (spec.get('levels') or [spec])))


def verify_gameplay(page, spec, directory, record):
    snap=lambda:page.evaluate('window.__AETHER_PLATFORMER__.snapshot()')
    def wait(expression, arg=None, timeout=4000):
        page.wait_for_function(expression,arg=arg,timeout=timeout)
    def teleport(x,y): page.evaluate('([x,y])=>window.__AETHER_PLATFORMER__.teleport(x,y)',[x,y])
    def press(key, duration=70):
        page.keyboard.down(key);page.wait_for_timeout(duration);page.keyboard.up(key)
    def restart(stage=0):
        generation=snap()['generation']
        page.evaluate('(stage)=>window.__AETHER_PLATFORMER__.restart(stage)',stage)
        wait('(g)=>window.__AETHER_PLATFORMER__?.snapshot().ready && window.__AETHER_PLATFORMER__.snapshot().generation>g',generation)
        wait('window.__AETHER_PLATFORMER__.snapshot().grounded')
    def activate(entity, level):
        floor=level['platforms'][entity['platform']]['y']*36
        mode=entity.get('activation','interact')
        platform=level['platforms'][entity['platform']]
        teleport(max(platform['x']*36+20,entity['x']-65) if mode=='projectile' else entity['x'],floor-28)
        page.wait_for_timeout(100)
        if mode=='interact': press('e')
        if mode=='projectile': press('f')
        wait('(id)=>window.__AETHER_PLATFORMER__.snapshot().progress.activate.includes(id)',entity['id'])
    def defeat(entity, level):
        # A falling body must really contact the enemy from above; no defeat injection.
        for _ in range(entity.get('ai',{}).get('health',1)+2):
            actor=next((e for e in snap()['enemies'] if e['id']==entity['id']),None)
            if actor is None: break
            if snap()['playerAttack']=='projectile':
                platform=level['platforms'][entity['platform']]
                teleport(max(platform['x']*36+20,actor['x']-85),platform['y']*36-28)
                press('ArrowRight',20);press('f');page.wait_for_timeout(380)
            else:
                teleport(actor['x'],actor['y']-75)
                page.wait_for_timeout(480)
        wait('(id)=>window.__AETHER_PLATFORMER__.snapshot().progress.defeat.includes(id)',entity['id'])
    levels=spec.get('levels') or [spec]
    page.locator('canvas').click()
    start=snap();press('ArrowRight',400)
    record('horizontal_movement',snap()['x']>start['x']+20,{'before':start,'after':snap()})
    restart();start=snap();press('Space');page.wait_for_timeout(140)
    record('jump',snap()['y']<start['y']-20,{'before':start,'after':snap()})
    # Independent mechanic probes may restart. The subsequent campaign path does not.
    for stage, level in enumerate(levels):
        resolved={**spec,**{key:value for key,value in level.items() if value is not None}}
        restart(stage)
        record('environment_composition',snap()['environment']==resolved['theme'] and not snap()['missingAssets'],{'stage':stage,'snapshot':snap()},'fidelity')
        for behavior in sorted({e.get('behavior','patrol') for e in level['entities'] if e['kind']=='enemy'}):
            restart(stage)
            enemy=next(e for e in level['entities'] if e['kind']=='enemy' and e.get('behavior','patrol')==behavior)
            actor=next(e for e in snap()['enemies'] if e['id']==enemy['id'])
            platform=level['platforms'][enemy['platform']]
            if behavior=='patrol':
                before=actor;page.wait_for_timeout(350)
                after=next(e for e in snap()['enemies'] if e['id']==enemy['id'])
                passed=abs(before['x']-after['x'])>5
            elif behavior=='chase':
                teleport(actor['x']-65,actor['y']);page.wait_for_timeout(100)
                before=next(e for e in snap()['enemies'] if e['id']==enemy['id'])
                teleport(actor['x']+65,actor['y']);page.wait_for_timeout(100)
                after=next(e for e in snap()['enemies'] if e['id']==enemy['id'])
                passed=before['vx']<0 and after['vx']>0
            else:
                x=actor['x']+85 if actor['x']+85<(platform['x']+platform['width'])*36-20 else actor['x']-75
                teleport(x,platform['y']*36-28)
                wait('(id)=>window.__AETHER_PLATFORMER__.snapshot().enemies.some(e=>e.id===id&&e.phase==="windup")',enemy['id'])
                before=snap();page.wait_for_timeout(enemy.get('ai',{}).get('telegraph_ms',450)+220);after=snap()
                a=next((e for e in after['enemies'] if e['id']==enemy['id']),None)
                old=next(e for e in before['enemies'] if e['id']==enemy['id'])
                passed=(a is not None and abs(a['x']-old['x'])>15) if behavior=='ambusher' else after['shotsFired']>before['shotsFired'] and any(e['phase']=='windup' for e in before['enemies'])
            record('enemy_'+behavior,passed,{'stage':stage,'method':'Actual decision state, motion or telegraphed projectile attack; controlled player placement','before':before,'after':after},'fidelity')
        if any(p['moving'] for p in level['platforms']):
            restart(stage)
            sources={s for p in level['platforms'] for s in p.get('activation_sources',[])}
            dormant=snap()['movingPlatforms'];page.wait_for_timeout(200);still=snap()['movingPlatforms']
            for source in sources:activate(next(e for e in level['entities'] if e['id']==source),level)
            before=snap()['movingPlatforms'];samples=[before]
            for _ in range(5):page.wait_for_timeout(150);samples.append(snap()['movingPlatforms'])
            after=samples[-1]
            moved=any(max(s[i]['x'] for s in samples)-min(s[i]['x'] for s in samples)+max(s[i]['y'] for s in samples)-min(s[i]['y'] for s in samples)>8 for i in range(len(before)))
            record('moving_platform_motion',moved,{'stage':stage,'samples':samples},'fidelity')
            if sources:record('switch_world_effects',dormant==still and moved,{'sources':sorted(sources),'dormant':dormant,'still':still,'samples':samples},'fidelity')
            sprites=[p for p in level['platforms'] if p['moving'] or p.get('route')=='optional']
            vertical=next((i for i,p in enumerate(sprites) if p['moving'] and p.get('motion',{}).get('axis')=='vertical'),None)
            if vertical is not None:
                restart(stage);platform=snap()['movingPlatforms'][vertical]
                teleport(platform['x'],platform['y']-48)
                wait('window.__AETHER_PLATFORMER__.snapshot().grounded')
                before=snap();samples=[before]
                for _ in range(4):
                    page.wait_for_timeout(sprites[vertical].get('motion',{}).get('period_ms',3000)/16);samples.append(snap())
                after=samples[-1]
                positions=[sample['movingPlatforms'][vertical]['y'] for sample in samples]
                offsets=[sample['y']-sample['movingPlatforms'][vertical]['y'] for sample in samples]
                record('vertical_platform_ride',max(positions)-min(positions)>5 and max(offsets)-min(offsets)<10,{'samples':samples})
                page.keyboard.down('Space')
                wait('(index)=>{const s=window.__AETHER_PLATFORMER__.snapshot();return !s.grounded&&s.y<s.movingPlatforms[index].y-55;}',vertical,2000)
                page.keyboard.up('Space')
                record('jump_from_vertical_platform',True,{'before':after,'after':snap()})
        if any(e['kind']=='timed_hazard' for e in level['entities']):
            restart(stage);values=[]
            hazard=next(e for e in level['entities'] if e['kind']=='timed_hazard')
            for _ in range(14):
                values.append(snap()['machines'][0]['active']);page.wait_for_timeout(hazard.get('period_ms',2200)/12)
            record('timed_hazard_cycle',len(set(values))==2,{'stage':stage,'active_samples':values},'fidelity')
            for source in {s for e in level['entities'] for s in e.get('disabled_by',[])}:
                activate(next(e for e in level['entities'] if e['id']==source),level)
                disabled=[]
                for _ in range(5):
                    page.wait_for_timeout(hazard.get('period_ms',2200)/4);disabled.append(any(m['active'] for m in snap()['machines']))
                record('switch_world_effects',not any(disabled),{'source':source,'disabled_samples':disabled},'fidelity')
        if resolved.get('player_attack')=='projectile' and any(e['kind']=='enemy' for e in level['entities']):
            restart(stage)
            enemy=max((e for e in level['entities'] if e['kind']=='enemy'),key=lambda e:e.get('ai',{}).get('health',1))
            platform=level['platforms'][enemy['platform']]
            teleport(platform['x']*36+22,platform['y']*36-28)
            for hit in range(enemy.get('ai',{}).get('health',1)):
                press('f');page.wait_for_timeout(140)
                if hit==0 and enemy.get('ai',{}).get('health',1)>1:
                    damaged=next((e for e in snap()['enemies'] if e['id']==enemy['id']),None)
                    record('enemy_damage_reaction',damaged is not None and damaged['health']==enemy['ai']['health']-1 and damaged['phase']=='hurt',snap())
                page.wait_for_timeout(240)
            record('player_projectile',enemy['id'] in snap()['progress']['defeat'] and snap()['playerShotsFired']>0,{'stage':stage,'snapshot':snap()},'fidelity')
        for link in (link for link in level.get('links',[]) if len(link['sources'])>1):
            restart(stage)
            sequence=[]
            gate=next(e for e in level['entities'] if e['kind']=='exit')
            for index,source in enumerate(link['sources']):
                entity=next(e for e in level['entities'] if e['id']==source)
                activate(entity,level)
                current=snap();door=next(d for d in current['doors'] if d['id']==link['target'])
                last=index==len(link['sources'])-1
                sequence.append({'activated':source,'open':door['open'],'collidable':door['collidable'],'expected_open':last})
                if not last:
                    teleport(gate['x'],gate['y']);page.wait_for_timeout(100)
                    sequence[-1]['exit_blocked']=snap()['state']=='playing'
            valid=all(s['open']==s['expected_open'] and s['collidable']!=s['expected_open'] and s.get('exit_blocked',True) for s in sequence)
            record('shared_gate_dependency',valid,{'method':'Real E/pressure/projectile activation, physical door body state and early exit overlap; controlled positions only','sequence':sequence,'feedback':snap().get('feedback',{})},'fidelity')
        for entity in (e for e in level['entities'] if e['kind'] in ('switch','pressure_plate')):
            restart(stage)
            link=next((link for link in level.get('links',[]) if link['sources']==[entity['id']]),None)
            door=next((e for e in level['entities'] if link and e['id']==link['target']),None)
            if door:
                teleport(door['x']-60,door['y']);page.keyboard.down('ArrowRight')
                wait('(x)=>{const s=window.__AETHER_PLATFORMER__.snapshot();return s.x>x-36&&s.x<x-20&&Math.abs(s.vx)<1;}',door['x'],2000)
                page.keyboard.up('ArrowRight')
                record('closed_door_collision',door['x']-40<snap()['x']<door['x']-20,{'stage':stage,'snapshot':snap()})
            activate(entity,level)
            targets=[link['target'] for link in level.get('links',[]) if entity['id'] in link['sources'] and len(link['sources'])==1]
            current=snap()
            passed=entity['id'] in current['progress']['activate'] and all(any(d['id']==target and d['open'] and not d['collidable'] for d in current['doors']) for target in targets)
            name='pressure_plate' if entity['kind']=='pressure_plate' else 'projectile_switch' if entity.get('activation')=='projectile' else 'switch_door'
            record(name,passed,{'stage':stage,'method':'Actual pressure/contact/proximity/key or projectile activation and linked door body removal','snapshot':current},'fidelity')
            if door and not any(e['kind']=='exit' and e['platform']==door['platform'] for e in level['entities']):
                teleport(door['x']-60,door['y']);page.keyboard.down('ArrowRight')
                wait('(x)=>window.__AETHER_PLATFORMER__.snapshot().x>x+30',door['x'],1800)
                page.keyboard.up('ArrowRight')
                record('open_door_passage',snap()['x']>door['x']+15,{'stage':stage,'snapshot':snap()})
        deadlines=[goal for goal in level.get('goals',[]) if goal['kind']=='time_limit' and goal['seconds']<=3]
        if deadlines:
            restart(stage)
            wait('window.__AETHER_PLATFORMER__.snapshot().state==="lost"',timeout=6000)
            record('deadline_expiry',any(goal['failed'] for goal in snap()['goals']),snap())
            generation=snap()['generation'];press('r')
            wait('(g)=>window.__AETHER_PLATFORMER__?.snapshot().generation>g',generation)
            record('restart_after_timeout',snap()['levelIndex']==0 and snap()['state']=='playing' and not any(snap()['progress'].values()),snap())
    restart()
    # Complete connected levels without restarting between them: campaign event IDs persist.
    for stage, level in enumerate(levels):
        before=snap()
        gate=next(e for e in level['entities'] if e['kind']=='exit')
        if any(not goal['complete'] for goal in before['goals']):
            teleport(gate['x'],gate['y']);page.wait_for_timeout(100)
            record('objective_locked_exit',snap()['state']=='playing' and snap()['levelIndex']==stage,snap())
        for entity in level['entities']:
            if entity['kind'] in ('switch','pressure_plate'): activate(entity,level)
            if entity['kind']=='enemy' and (any(goal['kind']=='defeat' for goal in level.get('goals',[])) or any(goal['kind']=='defeat' for goal in spec.get('campaign_goals',[]))): defeat(entity,level)
            if entity['kind']=='crystal': teleport(entity['x'],entity['y']);page.wait_for_timeout(45)
        for goal in level.get('goals',[]):
            if goal['kind']=='survive':
                teleport(level['spawn']['x'],level['spawn']['y'])
                wait('(id)=>window.__AETHER_PLATFORMER__.snapshot().goals.find(g=>g.id===id)?.complete',goal['id'],goal['seconds']*1000+2000)
                record('survival_objective',True,snap(),'fidelity')
        completed=snap()
        record('objective_conditions',all(goal['complete'] for goal in completed['goals']),{'stage':stage,'snapshot':completed})
        if any(goal['kind']=='defeat' for goal in level.get('goals',[])): record('combat_objective',all(goal['complete'] for goal in completed['goals'] if goal['kind']=='defeat'),completed,'fidelity')
        if any(goal['kind']=='time_limit' for goal in level.get('goals',[])): record('timed_objective',not any(goal['failed'] for goal in completed['goals']),completed,'fidelity')
        page.screenshot(path=str(directory/f'level-{stage+1}.png'),full_page=True)
        teleport(gate['x'],gate['y'])
        if stage+1<len(levels):
            wait('(i)=>window.__AETHER_PLATFORMER__?.snapshot().levelIndex===i',stage+1)
            current=snap()
            record('level_transitions',current['crystals']==0 and current['checkpoint']==-1 and current['progress']['defeat']==completed['progress']['defeat'],{'before':completed,'after':current},'fidelity')
        else:
            wait('window.__AETHER_PLATFORMER__.snapshot().state==="won"')
            record('win_condition',True,snap())
    generation=snap()['generation'];press('r')
    wait('(g)=>window.__AETHER_PLATFORMER__?.snapshot().generation>g',generation)
    current=snap()
    record('restart_reset',current['levelIndex']==0 and not any(current['progress'].values()) and current['state']=='playing' and current['checkpoint']==-1,current)
    page.screenshot(path=str(directory/'gameplay.png'),full_page=True)
