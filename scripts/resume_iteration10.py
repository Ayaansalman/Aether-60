"""Recover saved fresh Gemini decisions after focused fixes; max one fresh design.

Historical failed jobs and their original evidence remain unchanged.
"""
import json,sys,os
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from fastapi.testclient import TestClient
from providers.factory import get_provider,set_custom_provider
from main import app
OUT=ROOT/'docs/evidence/iteration10'
os.environ['AETHER_ALLOW_FALLBACK']='0'
real=get_provider();fresh=0
for case in (sys.argv[1:] or ['garden','factory']):
    saved=json.loads((OUT/f'live-{case}/result.json').read_text(encoding='utf-8'))
    artifacts=saved['artifacts'];prompt=saved['job']['prompt']
    intent=artifacts.get('semantic_intent.json')
    if intent is None:intent=next(a['candidate'] for a in reversed(artifacts['design_validation.json']['attempts']) if a.get('candidate'))
    intent.pop('provenance',None);design=artifacts.get('game_design.json')
    class Resume:
        calls=0
        def complete(self,system,user):
            global fresh
            self.calls+=1
            if self.calls==1:return SimpleNamespace(text=json.dumps(intent),model='saved-live-gemini-interpretation',latency_ms=0,fallback_events=[])
            if design is not None and self.calls==2:return SimpleNamespace(text=json.dumps(design),model='saved-live-gemini-design',latency_ms=0,fallback_events=[])
            if fresh>=1:raise ValueError('Saved-decision recovery allows at most one additional live design completion')
            fresh+=1
            return real.complete(system,user)
    provider=Resume();set_custom_provider(provider)
    try:
        with TestClient(app) as client:
            gid=client.post('/api/v2/games',json={'prompt':prompt,'mode':'live','seed':7}).json()['game_id']
            result=client.get('/api/v2/games/'+gid).json();result['verification_provenance']='Recovered saved fresh Gemini decisions; garden may use one new designer completion, factory uses zero new provider calls'
            out=OUT/f'live-recovered-{case}';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print(json.dumps({'case':case,'id':gid,'status':result['job']['status'],'total_fresh_recovery_calls':fresh,'runtime':result['artifacts'].get('qa_report.json',{}).get('overall'),'semantic':result['artifacts'].get('semantic_requirement_report.json',{}).get('overall'),'failures':[e['detail'] for e in result['events'] if e['stage']=='FAILED']}),flush=True)
    finally:set_custom_provider(None)
