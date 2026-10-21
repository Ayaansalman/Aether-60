"""Adventure adapter for the existing persisted v2 generation lifecycle."""
import asyncio
import json
import os
from services import adventure, job_store
from services.orchestrator import get_artifacts_dir


async def run_adventure(gid, request, artifact, stage, browser_report, intent=None):
    artifact('game_intent.json',{'original_prompt':request.prompt,'genre':'adventure','routing':'Explicit genre/interaction phrases; separate adventure adapter'})
    stage('PLANNING','Planning top-down adventure with configured provider' if request.mode=='live' else 'Planning labeled deterministic adventure fixture','START')
    design,provenance=await asyncio.to_thread(adventure.plan,request.prompt,request.mode,lambda raw:artifact('model_design.json',raw),intent)
    if request.mode=='fixture':artifact('model_design.json',design.model_dump())
    artifact('provider.json',provenance)
    artifact('design_normalization.json',{'changes':provenance.get('normalizations',[])})
    artifact('interpretation_guard.json',adventure.enforce_requirements(design,request.prompt))
    artifact('game_design.json',design.model_dump());artifact('final_design.json',design.model_dump())
    artifact('game_intent.json',{'original_prompt':request.prompt,'genre':'adventure','setting':design.theme,
        'gameplay':{'combat':design.combat,'quests':[q.model_dump() for q in design.quests]},
        'areas':[a.model_dump() for a in design.areas],'unsupported':design.unsupported,'interpretation_source':provenance})
    job_store.update_job(gid,model_id=provenance['model'] or 'fixture',limitations=design.unsupported)
    stage('DESIGNING','Composing seeded connected areas, NPCs, inventory and event-driven quests')
    stage('SELECTING_ASSETS','Selecting one coherent registered visual family and semantic actor/quest resources')
    ir=adventure.construct(design,request.prompt,request.seed)
    artifact('world_plan.json',{'seed':ir.seed,'areas':[
        {'name':a.name,'method':'settlement and woodland zones' if a.environment in ('village','forest') else 'connected room graph',
         'zones':a.zones,'buildings':len(a.buildings),'trees':len(a.trees),
         'relationships':[{'actor':actor.id,'role':actor.kind,'location':{'x':actor.x,'y':actor.y},'requires':actor.requires} for actor in a.actors]}
        for a in ir.areas]})
    stage('VALIDATING_SPEC','Checking destination connectivity, dialogue references and quest prerequisites')
    validation=adventure.validate_world(ir);artifact('validation.json',validation)
    artifact('repair_report.json',{'attempts':[],'maximum':0,'scope':'Connected paths are constructed directly. Invalid resource/quest designs fail validation; no speculative runtime repair.'})
    if validation['overall']!='PASS':raise ValueError('Adventure prerequisites or destinations are unreachable. Inspect validation.json.')
    manifest=adventure.asset_manifest(ir.art);asset_check=adventure.validate_assets()
    if ir.art:
        from services.adventure_assets import redistribution_manifest
        artifact('asset_selection.json',ir.art.model_dump())
        artifact('asset_export_manifest.json',redistribution_manifest(ir.art))
    artifact('asset_manifest.json',manifest);artifact('asset_validation.json',asset_check)
    if asset_check['overall']!='PASS':raise ValueError('Adventure asset checksum validation failed')
    artifact('game_ir_v2.json',ir.model_dump())
    url=os.getenv('AETHER_FRONTEND_URL','http://localhost:5173').rstrip('/')+f'/studio/play/{gid}'
    job_store.update_job(gid,spec_json=ir.model_dump_json(),game_url=url)
    stage('BUILDING','Adventure Phaser adapter and licensed tilemaps ready')
    artifact('build_manifest.json',{'runtime':'Phaser 3 Arcade','adapter':'AdventureScene','genre':'adventure','schema_version':ir.schema_version,
        'seed':ir.seed,'game_url':url,'area_count':len(ir.areas),'combat':ir.combat,'gravity':0,
        'asset_pack':ir.art.pack_id if ir.art else 'kenney_tiny'})
    stage('TESTING','Running real Chromium adventure interaction checks','START')
    report=await asyncio.to_thread(browser_report,url,get_artifacts_dir()/gid,'adventure')
    artifact('qa_report_initial.json',report);artifact('qa_report.json',report)
    artifact('diagnosis.json',{'failures':[c for c in report['checks'] if not c['passed']],'repairs_applied':0})
    # Construction evidence is intentionally distinct from semantic prompt fidelity.
    ir.requirements=[{'id':f'quest_{i}','source':q.text,'constructed':True,
        'status':'verified' if report['overall']=='PASS' else 'constructed_unverified'} for i,q in enumerate(ir.quests)]
    artifact('requirement_report.json',{'overall':'PASS' if report['overall']=='PASS' else 'UNVERIFIED','requirements':ir.requirements,
        'scope':'Validated planned quest coverage; browser replays each planned goal. Arbitrary prompt semantic coverage is not certified.','unsupported':design.unsupported})
    artifact('game_ir_v2.json',ir.model_dump())
    from services.semantic_intent import fidelity
    semantic=fidelity(ir,intent,report);artifact('semantic_requirement_report.json',semantic)
    final='FAILED' if report['overall']=='FAIL' or semantic['overall']=='FAIL' else 'READY' if report['overall']=='PASS' and semantic['overall']=='PASS' and not design.unsupported else 'READY_WITH_WARNINGS'
    job_store.update_job(gid,spec_json=ir.model_dump_json(),latest_qa_json=json.dumps(report),qa_summary={
        'passed':sum(c['passed'] for c in report['checks']),'failed':sum(not c['passed'] for c in report['checks']),
        'critical_failed':[c['id'] for c in report['checks'] if not c['passed'] and c.get('critical',True)]})
    stage(final,'Adventure browser checks passed' if report['overall']=='PASS' else 'Adventure browser QA '+report['overall']+'; inspect recorded evidence')
    artifact('outcome.json',{'status':final,'visual_quality':'Screenshot review required; functional QA does not certify aesthetics.'})
