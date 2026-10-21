"""Check the user's exact survival prompt through the real API (fixture by default)."""
import json,sys,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1];mode=sys.argv[1] if len(sys.argv)>1 else 'fixture'
prompt=(ROOT/'docs/evidence/survival-fix/prompt.txt').read_text(encoding='utf-8')
out=ROOT/'docs/evidence/survival-fix'/('api-'+mode);out.mkdir(exist_ok=True)
with httpx.Client(timeout=20) as client:
 r=client.post('http://127.0.0.1:8000/api/v2/games',json={'prompt':prompt,'mode':mode,'seed':7});r.raise_for_status();gid=r.json()['game_id'];print('Submitted',mode,gid,flush=True)
 for _ in range(150):
  result=client.get('http://127.0.0.1:8000/api/v2/games/'+gid).json()
  if result['job']['status'] in ('READY','READY_WITH_WARNINGS','FAILED'):
   (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('Result',result['job']['status'],result['job']['game_url'],flush=True)
   for name in ('qa_report.json','semantic_requirement_report.json'):
    report=result['artifacts'].get(name,{});print(name,report.get('overall'),[(c['id'],c['details']) for c in report.get('checks',[]) if not c['passed']],flush=True)
   if result['job']['status']=='FAILED':print(result['events'][-1]['detail'],flush=True)
   break
  time.sleep(2)
