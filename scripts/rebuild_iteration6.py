"""Rebuild saved Iteration 6 Gemini designs after reviewed developer changes.

Preserves original IR/QA, makes no provider calls, then requests browser retests.
Use the same AETHER_DB_PATH/AETHER_ARTIFACTS_DIR as the isolated backend.
"""
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'aether-backend'))
sys.path.insert(0,str(ROOT/'scripts'))
from services import job_store
from services.adventure import construct, validate_world
from services.adventure_assets import redistribution_manifest, validate_catalog
from services.orchestrator import get_artifacts_dir
from schemas.adventure import AdventureDesign
from verify_iteration6 import request


if __name__=='__main__':
    api='http://127.0.0.1:8002';pending={}
    for name in ['village','crypt']:
        exported=ROOT/f'docs/evidence/iteration6/live-{name}.json'
        saved=json.loads(exported.read_text(encoding='utf-8'));gid=saved['job']['game_id']
        job=job_store.get_job(gid)
        assert job and job['status'] in ('READY','READY_WITH_WARNINGS','FAILED')
        directory=get_artifacts_dir()/gid
        record=directory/'iteration6_developer_rebuild.json'
        assert not record.exists(),'Do not overwrite original rebuild evidence'
        design=AdventureDesign.model_validate(saved['artifacts']['final_design.json'])
        ir=construct(design,job['prompt'],42)
        ir.requirements=[dict(r,status='constructed_unverified') for r in saved['artifacts']['game_ir_v2.json']['requirements']]
        validation=validate_world(ir);assert validation['overall']=='PASS',validation
        outputs={record.name:{'source':'Reviewed developer rebuild, zero provider calls',
            'reason':'Correct floor atlas cell and place settlement landmarks in the settlement',
            'before_ir':saved['artifacts']['game_ir_v2.json'],'before_qa':saved['artifacts']['qa_report.json']},
            'game_ir_v2.json':ir.model_dump(),'validation.json':validation,'asset_selection.json':ir.art.model_dump(),
            'asset_manifest.json':ir.art.model_dump(),'asset_export_manifest.json':redistribution_manifest(ir.art),
            'asset_validation.json':validate_catalog(),
            'world_plan.json':{'seed':ir.seed,'areas':[{'name':a.name,'zones':a.zones,'buildings':a.buildings,
                'relationships':[{'actor':b.id,'kind':b.kind,'x':b.x,'y':b.y,'requires':b.requires} for b in a.actors]} for a in ir.areas]}}
        paths=job['artifact_paths'][:]
        for file,value in outputs.items():
            (directory/file).write_text(json.dumps(value,indent=2),encoding='utf-8')
            if file not in paths:paths.append(file)
        job_store.update_job(gid,spec_json=ir.model_dump_json(),artifact_paths=paths,status='READY_WITH_WARNINGS',stage='READY_WITH_WARNINGS')
        request(api,f'/api/v2/games/{gid}/verify',{})
        pending[name]=(gid,exported)
    deadline=time.monotonic()+300
    while pending and time.monotonic()<deadline:
        for name,(gid,path) in list(pending.items()):
            report=request(api,f'/api/v2/games/{gid}')
            if report['job']['status'] in ('READY','READY_WITH_WARNINGS','FAILED'):
                path.write_text(json.dumps(report,indent=2),encoding='utf-8')
                print(name,gid,report['job']['status'],report['job']['qa_summary'],flush=True)
                assert report['job']['status']=='READY',report['job']['status']
                del pending[name]
        if pending:time.sleep(2)
    assert not pending,'Timed out waiting for browser retests'
