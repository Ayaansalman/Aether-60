"""Rebuild an existing saved adventure design with current code; makes zero model calls."""
import asyncio,json,sys,uuid
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from schemas.adventure import AdventureDesign
from services.semantic_intent import Intent
from services import job_store,event_store
from services.orchestrator import get_artifacts_dir
from routes.platformer import run,Generate
source_id=sys.argv[1]
source=job_store.get_job(source_id)
if not source:raise ValueError('Source job not found')
folder=get_artifacts_dir()/source_id
raw=json.loads((folder/'model_design.json').read_text(encoding='utf-8'))
intent_raw=json.loads((folder/'semantic_intent.json').read_text(encoding='utf-8'));intent_raw.pop('provenance',None)
intent=Intent.model_validate(intent_raw)
provider={'provider':'saved_design_rebuild','model':source['model_id'] or 'saved-design','live':False,'model_calls':0,'source_job':source_id}
def saved_plan(prompt,mode,raw_callback=None,intent=None):
    if raw_callback:raw_callback(raw)
    return AdventureDesign.model_validate(raw),provider
new_id=str(uuid.uuid4());job_store.create_job(new_id,source['prompt'],prompt_version='2.0')
event_store.add_event(new_id,'QUEUED','START','Rebuilding saved real-model adventure with current builder; zero new provider calls. Source '+source_id)
with patch('services.semantic_intent.interpret',return_value=(intent,provider)),patch('services.adventure.plan',side_effect=saved_plan):
    asyncio.run(run(new_id,Generate(prompt=source['prompt'],mode='fixture',seed=7)))
job=job_store.get_job(new_id);out=ROOT/'docs/evidence/dual-dungeon-fix';out.mkdir(exist_ok=True)
result={'source_job':source_id,'rebuilt_job':new_id,'model_calls':0,'status':job['status'],'url':job['game_url'],'artifacts':{}}
for name in job['artifact_paths']:
    result['artifacts'][name]=json.loads((get_artifacts_dir()/new_id/name).read_text(encoding='utf-8'))
(out/'rebuilt_job.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print({'game_id':new_id,'status':job['status'],'url':job['game_url']},flush=True)
for name in ['qa_report.json','semantic_requirement_report.json']:
    report=result['artifacts'].get(name,{})
    print(name,report.get('overall'),[c for c in report.get('checks',[]) if not c['passed']],flush=True)
