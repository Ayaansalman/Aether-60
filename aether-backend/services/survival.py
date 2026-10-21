"""Survival planning adapter reusing the registered ArenaScene and v2 lifecycle."""
import asyncio,json,re,hashlib,os
from schemas.survival import SurvivalDesign,SurvivalIR

def plan(prompt,mode,intent=None):
    if mode=='fixture':
        d=SurvivalDesign(premise=prompt[:240])
        health=re.search(r'(\d+)\s*(?:health|hp|hearts)',prompt,re.I)
        shots=re.search(r'(\d+)\s*bullets',prompt,re.I)
        interval=re.search(r'(\d+(?:\.\d+)?)\s*second',prompt,re.I)
        if health:d.player.max_health=int(health[1])
        if shots:d.survival_stream.shooter_shots=int(shots[1])
        if interval:d.survival_stream.shot_interval_ms=round(float(interval[1])*1000)
        return SurvivalDesign.model_validate(d.model_dump()),{'provider':'fixture','model':None,'live':False}
    from providers.factory import get_provider
    from providers.mock import MockModelProvider
    provider=get_provider()
    if isinstance(provider,MockModelProvider):raise ValueError('Live survival requires a configured provider')
    result=provider.complete('Design an Aether top-down bullet-dodging arena survival game, using the existing arena runtime. Return ONLY JSON, no code, matching schema. Preserve health, exact number of shots per shooter, interval in milliseconds, random type selection, random safe spawns and shooter expiry after its last bullet. Endless requests use survive_endless, target=0: no artificial win timer. Finite survival uses survive_seconds. This is evasion-only: no player attacks, quests, inventory, NPCs, doors or collectibles. Only chaser/shooter roles are supported here; report ONLY explicitly requested unavailable behavior in unsupported. Do not list unrequested quests, inventory, collectibles, player weapons or attacks as limitations; an evasion prompt does not request any of these. Use the prompt and semantic requirements, not a quest-adventure template. Schema: '+json.dumps(SurvivalDesign.model_json_schema())+'\nSemantic intent: '+json.dumps(intent),prompt)
    return SurvivalDesign.model_validate_json(re.sub(r'^```(?:json)?\s*|\s*```$','',result.text.strip())),{'provider':type(provider).__name__,'model':result.model,'live':True}

def construct(design,prompt,seed=None):
    return SurvivalIR(**dict(design.model_dump(),seed=seed if seed is not None else int(hashlib.sha256(prompt.encode()).hexdigest()[:8],16)),requirements=[{'source':'Endless evasion, randomized spawns, emitter lifecycle and restart','status':'constructed_unverified'}])

def enforce_requirements(design,prompt):
    """Keep raw output; remove only known unsolicited limitation categories."""
    changes=[];retained=[]
    checks={
        'player attacks, weapons, and offensive abilities':r'\b(?:player|hero|character|I)\s+(?:(?:can|must|should|will|may)\s+)?(?:shoot|fire|attack)|(?:give|equip).*\b(?:weapon|gun|sword|blaster)|\bmy (?:weapon|gun|sword)|\bplayer attacks\b',
        'quests, npcs, doors, inventory, and collectibles':r'\bquest|\bnpc|\bdoor|\binventory|\bcollectibl',
    }
    for value in design.unsupported:
        pattern=checks.get(value.lower().strip())
        if pattern and not re.search(pattern,prompt,re.I):changes.append({'field':'unsupported','before':value,'reason':'This category was not requested by the user; raw model response retained'})
        else:retained.append(value)
    design.unsupported=retained
    return {'changes':changes,'scope':'Known unsolicited warning categories only; unknown limitations are retained'}

async def run_survival(gid,request,artifact,stage,browser_report,intent):
    from services import job_store
    from services.orchestrator import get_artifacts_dir
    from services.semantic_intent import fidelity
    stage('PLANNING','Planning arena survival controls, spawning and emitter timing','START')
    design,provider=await asyncio.to_thread(plan,request.prompt,request.mode,intent)
    artifact('model_design.json',design.model_dump());artifact('provider.json',provider)
    artifact('interpretation_guard.json',enforce_requirements(design,request.prompt))
    artifact('game_design.json',design.model_dump());artifact('final_design.json',design.model_dump())
    artifact('game_intent.json',{'original_prompt':request.prompt,'genre':'arena_survival','semantic':intent})
    stage('DESIGNING','Composing continuous spawning and finite-life shooter behaviors')
    ir=construct(design,request.prompt,request.seed)
    stage('VALIDATING_SPEC','Validating player health, spawn bounds, emitter counts and intervals')
    artifact('validation.json',{'overall':'PASS','checks':[{'id':'typed_survival_contract','passed':True}],'scope':'Strict typed contract; runtime checks follow'})
    artifact('game_ir_v2.json',ir.model_dump())
    url=os.getenv('AETHER_FRONTEND_URL','http://localhost:5173').rstrip('/')+f'/studio/play/{gid}'
    job_store.update_job(gid,spec_json=ir.model_dump_json(),game_url=url,model_id=provider['model'] or 'fixture',limitations=design.unsupported)
    stage('BUILDING','Existing Phaser ArenaScene with registered survival stream components')
    artifact('build_manifest.json',{'adapter':'SurvivalCanvas','runtime':'ArenaScene','schema_version':'2.3','original_primitive_art':True})
    stage('TESTING','Checking real arena movement, bullets, emitter expiry and restart','START')
    report=await asyncio.to_thread(browser_report,url,get_artifacts_dir()/gid,'arena_survival')
    artifact('qa_report.json',report)
    ir.requirements[0]['status']='verified' if report['overall']=='PASS' else 'constructed_unverified'
    semantic=fidelity(ir,intent,report);artifact('semantic_requirement_report.json',semantic)
    artifact('requirement_report.json',{'overall':report['overall'],'requirements':ir.requirements,'scope':'Runtime checks and separate semantic bindings; not arbitrary prompt certification'})
    artifact('game_ir_v2.json',ir.model_dump())
    job_store.update_job(gid,spec_json=ir.model_dump_json(),latest_qa_json=json.dumps(report),qa_summary={'passed':sum(c['passed'] for c in report['checks']),'failed':sum(not c['passed'] for c in report['checks'])})
    final='FAILED' if report['overall']=='FAIL' or semantic['overall']=='FAIL' else 'READY' if report['overall']=='PASS' and semantic['overall']=='PASS' and not ir.unsupported else 'READY_WITH_WARNINGS'
    stage(final,'Survival runtime '+report['overall']+'; semantic fidelity '+semantic['overall'])
