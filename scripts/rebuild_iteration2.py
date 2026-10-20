"""Rebuild saved typed designs with current developer fixes; no provider call.

Preserves prior IR and reports an explicit developer rebuild, never an invented self-repair.
Run while the backend worker is idle, then request browser re-verification.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'aether-backend'))
from schemas.platformer import GameDesign
from services.platformer import enforce_explicit_requirements,construct,validate_route
from services.capabilities import requirement_evidence
from services import job_store,event_store
from services.orchestrator import get_artifacts_dir

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('ids',type=Path);args=parser.parse_args()
    for name,gid in json.loads(args.ids.read_text()).items():
        job=job_store.get_job(gid)
        if job['status'] not in ('READY','READY_WITH_WARNINGS','FAILED'):
            raise RuntimeError(f'{name} is still running; do not rebuild concurrently')
        directory=get_artifacts_dir()/gid
        read=lambda name:json.loads((directory/name).read_text(encoding='utf-8'))
        before=read('game_ir_v2.json')
        design=GameDesign.model_validate(read('final_design.json'))
        guard=enforce_explicit_requirements(design,job['prompt'])
        ir=construct(design,job['prompt'],before['seed'])
        validation=validate_route(ir)
        assert validation['overall']=='PASS'
        coverage=requirement_evidence(ir,job['prompt'],design.unsupported)
        assert coverage['overall']!='FAIL'
        record={'source':'Developer iteration rebuild; no model request or automatic repair is claimed',
                'reason':'Apply reviewed library, shrine/beacon/relic visuals, stage camera settings and alternate-route deduplication',
                'before':before,'after':ir.model_dump(),'validation':validation,'guard_changes':guard['changes']}
        assert not (directory/'iteration2_developer_rebuild.json').exists(), 'Preserve previous rebuild evidence; use a new revision name'
        outputs={'iteration2_developer_rebuild.json':record,'game_ir_v2.json':ir.model_dump(),
                 'final_design.json':design.model_dump(),'validation.json':validation,
                 'requirement_report.json':{**read('requirement_report.json'),**coverage}}
        manifest=read('build_manifest.json')
        manifest.update(developer_revision='iteration2-reviewed',level_count=len(ir.levels) or 1,exit_style=ir.exit_style,
                        capabilities=[r['id'] for r in coverage['requirements'] if r.get('constructed')],
                        source_sha256={file:hashlib.sha256((ROOT/file).read_bytes()).hexdigest() for file in
                            ['aether-backend/services/platformer.py','aether-frontend/src/game/platformer/PlatformerScene.ts','aether-frontend/src/game/platformer/behaviors.ts']})
        outputs['build_manifest.json']=manifest
        outputs['asset_manifest.json']=json.loads((ROOT/'aether-frontend/public/assets/registry.json').read_text(encoding='utf-8'))
        paths=list(job['artifact_paths'])
        for file,data in outputs.items():
            (directory/file).write_text(json.dumps(data,indent=2),encoding='utf-8')
            if file not in paths:paths.append(file)
        job_store.update_job(gid,spec_json=ir.model_dump_json(),artifact_paths=paths,status='READY_WITH_WARNINGS',stage='READY_WITH_WARNINGS')
        event_store.add_event(gid,stage='DEVELOPER_REBUILD',result='SUCCESS',detail='Reviewed iteration 2 implementation rebuilt this saved design from its original seed. Prior IR retained; browser retest pending.',rationale='Developer changes, not an autonomous repair event')
        print(name,gid,'rebuilt; browser retest required',flush=True)
