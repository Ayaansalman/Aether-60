"""Two fresh production prompts, one shared six-completion budget, real HTTP/QA.

Use --replay for zero-provider-call replay of the historical jobs instead.
"""
import json,sys,os
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from fastapi.testclient import TestClient
from providers.factory import get_provider,set_custom_provider
from main import app
OUT=ROOT/'docs/evidence/iteration10'

def main():
    replay='--replay' in sys.argv
    cases=[arg for arg in sys.argv[1:] if not arg.startswith('--')] or ['garden','factory']
    os.environ['AETHER_ALLOW_FALLBACK']='0'
    real=None if replay else get_provider()
    budget=6;total=0;results=[]
    for case in cases:
        source=json.loads((OUT/f'source-{case}.json').read_text(encoding='utf-8'));intent=source['semantic_intent.json'];intent.pop('provenance',None)
        class Provider:
            calls=0
            def complete(self,system,prompt):
                nonlocal total
                self.calls+=1;total+=1
                if total>budget:raise ValueError('Iteration 10 live verification completion budget reached')
                if not replay:return real.complete(system,prompt)
                if self.calls>2:raise ValueError('Captured replay unexpectedly requested model repair')
                return SimpleNamespace(text=json.dumps(intent if self.calls==1 else source['game_design.json']),model='captured-gemini-replay',latency_ms=0,fallback_events=[])
        provider=Provider();set_custom_provider(provider)
        out=OUT/(('api-replay-' if replay else 'live-')+case);out.mkdir(exist_ok=True)
        try:
            with TestClient(app) as client:
                response=client.post('/api/v2/games',json={'prompt':source['prompt'],'mode':'live','seed':7});response.raise_for_status()
                gid=response.json()['game_id'];result=client.get('/api/v2/games/'+gid).json()
                result['verification_provenance']='Captured Gemini decisions; zero fresh provider calls' if replay else 'Fresh configured Gemini interpretation/design; actual persisted HTTP pipeline and Chromium QA'
                result['completion_calls']=provider.calls
                (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
                summary={'case':case,'id':gid,'status':result['job']['status'],'calls':provider.calls,'runtime':result['artifacts'].get('qa_report.json',{}).get('overall'),'semantic':result['artifacts'].get('semantic_requirement_report.json',{}).get('overall'),'failures':[e['detail'] for e in result['events'] if e['stage']=='FAILED']}
                results.append(summary);print(json.dumps(summary),flush=True)
        finally:set_custom_provider(None)
        (OUT/('api-replay-results.json' if replay else 'live-results.json')).write_text(json.dumps(results,indent=2),encoding='utf-8')

if __name__=='__main__':main()
