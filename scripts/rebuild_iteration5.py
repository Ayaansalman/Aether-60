"""Apply reviewed builder changes to the two saved live designs, without provider calls.

Run with the backend's AETHER_DB_PATH / AETHER_ARTIFACTS_DIR, while workers are idle.
Original raw output, IR and QA remain in the developer-rebuild artifact.
"""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'aether-backend'))
from services import job_store,event_store
from services.adventure import construct,enforce_requirements,validate_world
from schemas.adventure import AdventureDesign
from services.orchestrator import get_artifacts_dir


if __name__=='__main__':
    for name in ['village','dungeon']:
        exported=json.loads((ROOT/f'docs/evidence/iteration5/live/{name}.json').read_text(encoding='utf-8'))
        gid=exported['job']['game_id'];job=job_store.get_job(gid)
        assert job['status'] in ('READY','READY_WITH_WARNINGS','FAILED'), 'Worker must be idle'
        directory=get_artifacts_dir()/gid
        assert not (directory/'iteration5_developer_rebuild.json').exists(), 'Preserve prior rebuild'
        design=AdventureDesign.model_validate(exported['artifacts']['model_design.json'])
        changes=enforce_requirements(design,job['prompt']);ir=construct(design,job['prompt'],42)
        validation=validate_world(ir);assert validation['overall']=='PASS',validation
        ir.requirements=[{'id':f'quest_{i}','source':q.text,'constructed':True,'status':'constructed_unverified'} for i,q in enumerate(ir.quests)]
        outputs={
            'iteration5_developer_rebuild.json':{'source':'Developer rebuild of saved Gemini designs; no provider call or autonomous repair',
                'reason':'Scattered pickups, physical sealed passages, complete multi-item deliveries and grounded text/limitations',
                'before_ir':exported['artifacts']['game_ir_v2.json'],'before_qa':exported['artifacts']['qa_report.json'],'guard':changes},
            'game_ir_v2.json':ir.model_dump(),'game_design.json':design.model_dump(),'final_design.json':design.model_dump(),'validation.json':validation,
            'game_intent.json':{**exported['artifacts']['game_intent.json'],'gameplay':{'combat':design.combat,'quests':[q.model_dump() for q in design.quests]},'unsupported':design.unsupported},
            'interpretation_guard.json':changes,
            'requirement_report.json':{'overall':'UNVERIFIED','requirements':ir.requirements,'scope':'Developer rebuild; browser re-verification pending'},
        }
        paths=list(job['artifact_paths'])
        for file,data in outputs.items():
            (directory/file).write_text(json.dumps(data,indent=2),encoding='utf-8')
            if file not in paths:paths.append(file)
        job_store.update_job(gid,spec_json=ir.model_dump_json(),artifact_paths=paths,limitations=design.unsupported,status='READY_WITH_WARNINGS',stage='READY_WITH_WARNINGS')
        event_store.add_event(gid,stage='DEVELOPER_REBUILD',result='SUCCESS',detail='Reviewed adventure changes rebuilt the saved Gemini design. Original IR and QA retained. Browser re-verification pending.',rationale='Developer work; no new provider request')
        print(name,gid,'rebuilt; re-verify through API',flush=True)
