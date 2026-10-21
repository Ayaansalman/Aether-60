"""Reviewable visual-only upgrade of idle local jobs; keeps geometry and original AI designs.

Run with the job database/artifact environment variables and re-verify via the API afterwards.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from services import job_store,event_store
from services.orchestrator import get_artifacts_dir
from services.adventure_assets import choose_art,redistribution_manifest,validate_catalog
from schemas.adventure import AdventureDesign,AdventureIR


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('ids',nargs='+');p.add_argument('--revision',type=int,default=1);args=p.parse_args()
    validation=validate_catalog();assert validation['overall']=='PASS',validation
    for gid in args.ids:
        job=job_store.get_job(gid);assert job and job['status'] in ('READY','READY_WITH_WARNINGS','FAILED')
        directory=get_artifacts_dir()/gid;before=json.loads(job['spec_json']);ir=AdventureIR.model_validate(before)
        design=AdventureDesign.model_validate_json((directory/'final_design.json').read_text(encoding='utf-8'))
        record=directory/f'asset_upgrade_v{args.revision}.json';assert not record.exists(),'Preserve prior upgrade evidence'
        original=ir.model_dump(exclude={'art'})
        ir.art=choose_art(design,job['prompt'],ir.seed)
        assert ir.model_dump(exclude={'art'})==original,'Visual upgrades must preserve gameplay and geometry'
        outputs={record.name:{'source':'Developer visual-only upgrade; no model call or map rebuild',
            'before_ir':before,'geometry_and_gameplay_unchanged':True,'selected_pack':ir.art.pack_id},
            'game_ir_v2.json':ir.model_dump(),'asset_selection.json':ir.art.model_dump(),'asset_manifest.json':ir.art.model_dump(),
            'asset_export_manifest.json':redistribution_manifest(ir.art),'asset_validation.json':validation}
        build=json.loads((directory/'build_manifest.json').read_text(encoding='utf-8'));build['asset_pack']=ir.art.pack_id;build['developer_revision']='adventure-art-library-v1';outputs['build_manifest.json']=build
        paths=job['artifact_paths'][:]
        for name,data in outputs.items():
            (directory/name).write_text(json.dumps(data,indent=2),encoding='utf-8')
            if name not in paths:paths.append(name)
        job_store.update_job(gid,spec_json=ir.model_dump_json(),artifact_paths=paths,status='READY_WITH_WARNINGS',stage='READY_WITH_WARNINGS',
            qa_summary={'passed':0,'failed':0,'critical_failed':[],'scope':'Visual asset upgrade; browser re-verification pending'})
        event_store.add_event(gid,stage='SELECTING_ASSETS',result='SUCCESS',detail=f'Developer upgrade selected the registered {ir.art.pack_id} family. Original IR retained; no geometry, quest or provider change. Browser verification pending.',rationale='Reviewed asset integration, not a new model invocation')
        print(gid,ir.art.pack_id,'upgraded; re-verification required',flush=True)
