"""Validated model design and deterministic arcade adapter."""
import hashlib,json,re,asyncio,os
from schemas.runner import RunnerDesign,RunnerIR

def plan(prompt,mode,intent=None):
    if mode=='fixture':
        return fixture_design(prompt), {'provider':'fixture','model':None,'live':False}
    from providers.factory import get_provider
    from providers.mock import MockModelProvider
    provider=get_provider()
    if isinstance(provider,MockModelProvider):raise ValueError('Live runner requires configured provider')
    system='Design a playable original arcade runner. Return only JSON. ground means automatic forward motion and grounded jump; flap means gravity and repeatable upward impulse. Choose easy/medium/hard/extreme difficulty and stable/gradual/surge progression from the request. Omit numerical tuning to use that difficulty profile, or supply deliberate values. Challenge recovery is grounded time between jumps; spacing is seconds between flying gates; precision is fraction of safe jump width; transition is maximum flying height change in pixels. Choose ground patterns from single/rhythm/escalation/mixed/recovery; flap patterns from single/alternating/ascending/descending/corridor/recovery. Patterns vary in length and geometry, with periodic recovery. Use exclusions for forbidden obstacle families. Choose factory for industrial machinery, neon for city, forest, sky or ice. Bird and creature are supported players. Preserve environmental theme, character, pacing, finite/endless, scoring and constraints. Unavailable special mechanics must be recorded in unsupported. No generated code. Schema: '+json.dumps(RunnerDesign.model_json_schema())+'\nSemantic intent: '+json.dumps(intent)
    result=provider.complete(system,prompt)
    from services.design_validation import validated_response
    arcade=(intent or {}).get('arcade') or {}
    bindings=[]
    def prepare(raw):
        for key,value in arcade.items():
            if value is not None:
                if raw.get(key)!=value:bindings.append({'field':key,'model_value':raw.get(key),'semantic_value':value})
                raw[key]=value
        return raw
    design,attempts=validated_response(provider,system,prompt,result,RunnerDesign,prepare)
    return design,{'provider':type(provider).__name__,'model':attempts[-1]['model'],'live':True,'intent_bindings':bindings,'validation_attempts':attempts}


def fixture_design(prompt):
    """Offline fixtures only; live designs use the semantic and designer models."""
    p=prompt.lower();flap=bool(re.search(r'flap|tap.*(?:fly|airborne)|flying.*(?:tap|space)',p))
    difficulty='extreme' if re.search(r'extrem|very difficult',p) else 'hard' if re.search(r'\bhard\b|\bdifficult\b|precision',p) else 'easy' if re.search(r'\beasy\b|beginner|relax|forgiving',p) else 'medium'
    theme='ice' if re.search(r'ic[ey]|icy|snow|frozen',p) else 'factory' if re.search(r'factory|industrial',p) else 'forest' if re.search(r'forest|woodland',p) else 'neon' if re.search(r'neon|cyber|city',p) else 'sky'
    data=dict(mode='flap' if flap else 'ground',difficulty=difficulty,theme=theme,player='bird' if flap else 'creature' if re.search(r'creature|woodland',p) else 'robot',endless=not bool(re.search(r'finite|finish line',p)),progression='stable' if re.search(r'stable|constant|no (?:speed|difficulty) (?:increase|progression)',p) else 'surge' if 'surge' in p else 'gradual')
    data['title']={'forest':'Mosslight','factory':'Foundry','ice':'Frostbite','sky':'Cloudwing','neon':'Neon'}[theme]+(' Flight' if flap else ' Sprint')
    exclusions=[k for k in ['spike','gap','laser','barrier'] if re.search(r'(?:no|without|exclude) '+k,p)]
    data['exclusions']=exclusions
    mentioned=[k for k in ['spike','gap','laser','barrier'] if k in p and k not in exclusions]
    if mentioned and not flap:data['obstacles']=mentioned
    elif theme=='forest':data['obstacles']=['spike','gap','barrier']
    return RunnerDesign(**data)

def construct(design,prompt,seed=None):
    return RunnerIR(**design.model_dump(),seed=seed if seed is not None else int(hashlib.sha256(prompt.encode()).hexdigest()[:8],16),requirements=[{'source':'Runner control, procedural obstacles, score and restart','status':'constructed_unverified'}])

async def run_runner(gid,request,artifact,stage,browser_report,intent=None):
    from services import job_store
    from services.orchestrator import get_artifacts_dir
    stage('PLANNING','Planning validated arcade controls and survival loop','START')
    design,provider=await asyncio.to_thread(plan,request.prompt,request.mode,intent)
    artifact('model_design.json',design.model_dump());artifact('provider.json',provider)
    artifact('design_validation.json',{'attempts':provider.get('validation_attempts',[]),'maximum_corrections':1})
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
    artifact('build_manifest.json',{'adapter':'RunnerCanvas','genre':'runner','mode':ir.mode,'art':'selected bundled Kenney CC0 pixel atlases and original pixel compositions','theme':ir.theme,'challenge':ir.challenge.model_dump(),'difficulty':ir.difficulty,'physics':'ballistic jump envelope and bounded flap reachability at speed endpoints','bounded_active_world':True})
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
