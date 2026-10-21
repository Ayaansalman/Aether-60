"""Validated model design and deterministic arcade adapter."""
import hashlib,json,re,asyncio,os
from schemas.runner import RunnerDesign,RunnerIR

def plan(prompt,mode,intent=None):
    if mode=='fixture':
        p=prompt.lower();flap=bool(re.search(r'flap|tap.*(?:fly|airborne)|flying.*(?:tap|space)',p))
        return RunnerDesign(mode='flap' if flap else 'ground',theme='sky' if flap else 'neon' if re.search(r'neon|cyber|factory|city',p) else 'ice' if 'ice' in p else 'forest',player='creature' if flap else 'robot',endless=not bool(re.search(r'finite|finish line',p)),speed=340 if 'fast' in p else 280,acceleration=2 if re.search(r'faster|challeng|difficulty',p) else 0), {'provider':'fixture','model':None,'live':False}
    from providers.factory import get_provider
    from providers.mock import MockModelProvider
    provider=get_provider()
    if isinstance(provider,MockModelProvider):raise ValueError('Live runner requires configured provider')
    result=provider.complete('Design a playable original arcade runner. Return only JSON. ground means automatic forward motion and grounded jump; flap means gravity and repeatable upward impulse, never grounded jump. Use appropriate theme, presentation, obstacles, speed curve, endless/finite and scoring from user. Physics are bounded by schema and fair obstacle spacing is computed by runtime. Record requested unavailable features in unsupported. No code. Schema: '+json.dumps(RunnerDesign.model_json_schema())+'\nSemantic intent: '+json.dumps(intent),prompt)
    return RunnerDesign.model_validate_json(re.sub(r'^```(?:json)?\s*|\s*```$','',result.text.strip())),{'provider':type(provider).__name__,'model':result.model,'live':True}

def construct(design,prompt,seed=None):
    return RunnerIR(**design.model_dump(),seed=seed if seed is not None else int(hashlib.sha256(prompt.encode()).hexdigest()[:8],16),requirements=[{'source':'Runner control, procedural obstacles, score and restart','status':'constructed_unverified'}])

async def run_runner(gid,request,artifact,stage,browser_report,intent=None):
    from services import job_store
    from services.orchestrator import get_artifacts_dir
    stage('PLANNING','Planning validated arcade controls and survival loop','START')
    design,provider=await asyncio.to_thread(plan,request.prompt,request.mode,intent)
    artifact('model_design.json',design.model_dump());artifact('provider.json',provider)
    artifact('final_design.json',design.model_dump());artifact('game_design.json',design.model_dump())
    artifact('game_intent.json',{'original_prompt':request.prompt,'genre':'runner','control':design.mode,'endless':design.endless,'semantic':intent})
    stage('DESIGNING','Composing seeded obstacle stream and selected movement controller')
    ir=construct(design,request.prompt,request.seed)
    stage('VALIDATING_SPEC','Checking typed movement bounds, scoring and obstacle configuration')
    RunnerIR.model_validate(ir.model_dump())
    artifact('validation.json',{'overall':'PASS','checks':[{'id':'typed_runner_configuration','passed':True}],'scope':'Schema and physics constraints; obstacle spacing is calculated at runtime and tested separately'})
    artifact('game_ir_v2.json',ir.model_dump())
    stage('BUILDING','Registered canvas runtime and bounded procedural stream ready')
    url=os.getenv('AETHER_FRONTEND_URL','http://localhost:5173').rstrip('/')+f'/studio/play/{gid}'
    job_store.update_job(gid,spec_json=ir.model_dump_json(),game_url=url,model_id=provider['model'] or 'fixture',limitations=design.unsupported)
    artifact('build_manifest.json',{'adapter':'RunnerCanvas','genre':'runner','mode':ir.mode,'art':'original canvas primitives','bounded_active_world':True})
    stage('TESTING','Running Chromium arcade checks','START')
    report=await asyncio.to_thread(browser_report,url,get_artifacts_dir()/gid,'runner')
    artifact('qa_report.json',report)
    ir.requirements[0]['status']='verified' if report['overall']=='PASS' else 'failed' if report['overall']=='FAIL' else 'constructed_unverified'
    artifact('requirement_report.json',{'overall':report['overall'],'requirements':ir.requirements,'unsupported':ir.unsupported,'scope':'Runtime checks; arbitrary semantic coverage is not certified'})
    artifact('game_ir_v2.json',ir.model_dump())
    job_store.update_job(gid,spec_json=ir.model_dump_json(),latest_qa_json=json.dumps(report),qa_summary={'passed':sum(c['passed'] for c in report['checks']),'failed':sum(not c['passed'] for c in report['checks'])})
    from services.semantic_intent import fidelity
    semantic=fidelity(ir,intent,report);artifact('semantic_requirement_report.json',semantic)
    stage('FAILED' if report['overall']=='FAIL' or semantic['overall']=='FAIL' else 'READY' if report['overall']=='PASS' and semantic['overall']=='PASS' and not ir.unsupported else 'READY_WITH_WARNINGS','Arcade checks '+report['overall'])
