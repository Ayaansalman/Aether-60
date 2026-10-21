"""Replay captured genuine model decisions through the actual persisted API + Chromium pipeline, without further provider calls."""
import sys,json
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from fastapi.testclient import TestClient
from providers.factory import set_custom_provider
from tests.test_iteration9 import A,D
from main import app
case=sys.argv[1] if len(sys.argv)>1 else 'A';out=ROOT/'docs/evidence/iteration9'/('api-replay-'+case);out.mkdir(parents=True,exist_ok=True)
capture=ROOT/'docs/evidence/iteration9'/('live-'+case)
intent=json.loads((capture/'intent.json').read_text(encoding='utf-8'));intent.pop('provenance',None)
design=json.loads((capture/'design.json').read_text(encoding='utf-8'))
class CapturedGeminiReplay:
    calls=0
    def complete(self,system,user):
        self.calls+=1
        if self.calls>2:raise AssertionError('Unexpected model repair in captured replay')
        return SimpleNamespace(text=json.dumps(intent if self.calls==1 else design),model='captured-gemini-3.5-flash-lite',latency_ms=0,fallback_events=[])
p=CapturedGeminiReplay();set_custom_provider(p)
try:
    with TestClient(app) as client:
        result=client.post('/api/v2/games',json={'prompt':{'A':A,'D':D}[case],'mode':'live','seed':7});result.raise_for_status();gid=result.json()['game_id']
        response=client.get('/api/v2/games/'+gid).json();response['verification_provenance']='Captured real Gemini semantic/design replay through HTTP API and actual browser; no new provider calls.'
        (out/'result.json').write_text(json.dumps(response,indent=2),encoding='utf-8')
        print(case,gid,response['job']['status'],flush=True)
        print('Runtime',response['artifacts'].get('qa_report.json',{}).get('overall'),'Semantic',response['artifacts'].get('semantic_requirement_report.json',{}).get('overall'),flush=True)
finally:set_custom_provider(None)
