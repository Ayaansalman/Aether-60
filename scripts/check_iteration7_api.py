"""Bounded actual API integration: one fixture or two live model calls (intent + design)."""
import sys,time,json,httpx,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from tests.test_iteration7 import A,B,C,D
mode=sys.argv[1] if len(sys.argv)>1 else 'fixture';case=sys.argv[2] if len(sys.argv)>2 else 'D'
out=ROOT/'docs/evidence/iteration7'/('api-'+mode+'-'+case);out.mkdir(parents=True,exist_ok=True)
with httpx.Client(timeout=30) as client:
    response=client.post(os.getenv('AETHER_TEST_API_URL','http://localhost:8000')+'/api/v2/games',json={'prompt':dict(A=A,B=B,C=C,D=D)[case],'mode':mode,'seed':7});response.raise_for_status();gid=response.json()['game_id'];print('Submitted',gid,mode,case,flush=True)
    for _ in range(100):
        result=client.get(os.getenv('AETHER_TEST_API_URL','http://localhost:8000')+'/api/v2/games/'+gid).json()
        state=result['job']['status']
        if state in ['READY','READY_WITH_WARNINGS','FAILED']:
            (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('Result',state,'Artifacts',list(result['artifacts']),flush=True)
            if result['job'].get('spec_json'):print('Spec persisted',flush=True)
            break
        time.sleep(2)
    else:print('Timed out waiting; job remains running',flush=True)
