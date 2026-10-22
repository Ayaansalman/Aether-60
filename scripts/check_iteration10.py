"""Captured jobs through real Chromium adapters; no provider/network model calls."""
import json,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from providers.factory import set_custom_provider
from services import adventure,platformer,runner
from services.semantic_intent import interpret,fidelity,feasibility
from services.adventure_qa import run_browser_qa as adventure_qa
from services.platformer_qa import run_browser_qa as platformer_qa
from services.boss_qa import run_browser_qa as boss_qa
from services.runner_qa import run_browser_qa as runner_qa
from services.composition_qa import run_browser_qa as composition_qa
from tests.test_iteration9 import design,behavior
OUT=ROOT/'docs/evidence/iteration10'

def save(path,data):path.write_text(json.dumps(data,indent=2),encoding='utf-8')

def prepare(case):
    source=json.loads((OUT/f'source-{case}.json').read_text(encoding='utf-8'))
    raw_intent=source['semantic_intent.json'];raw_intent.pop('provenance',None)
    class Replay:
        calls=0
        def complete(self,system,prompt):
            self.calls+=1
            if self.calls>2:raise AssertionError('Unexpected paid repair request')
            return SimpleNamespace(text=json.dumps(raw_intent if self.calls==1 else source['game_design.json']),model='captured-gemini',latency_ms=0,fallback_events=[])
    provider=Replay();set_custom_provider(provider)
    try:
        intent,provenance=interpret(source['prompt'],'live');data=intent.model_dump()
        compatibility=feasibility(data)
        if compatibility['overall']=='FAIL':return None,data,compatibility,None
        adapter=adventure if intent.genre=='adventure' else runner if intent.genre=='runner' else platformer
        d,planning=adapter.plan(source['prompt'],'live',intent=data)
        guard=adventure.enforce_requirements(d,source['prompt']) if adapter==adventure else platformer.enforce_explicit_requirements(d,source['prompt']) if adapter==platformer else {}
        ir=adapter.construct(d,source['prompt'],7)
        directory=OUT/case;directory.mkdir(exist_ok=True)
        for name,value in [('spec',ir.model_dump()),('intent',data),('design',d.model_dump()),('guard',guard),('provider',planning),('interpretation',provenance)]:save(directory/(name+'.json'),value)
        return ir,data,compatibility,adapter
    finally:set_custom_provider(None)

def main():
    results=[]
    for case in (sys.argv[1:] or ['factory','garden','boss','runner','laboratory','open','easy','guardian']):
        directory=OUT/case;directory.mkdir(exist_ok=True)
        if case in ('laboratory','open'):
            config=behavior(3,500,4);config.outcome='survive';config.duration_seconds=60
            ir=adventure.construct(design(config),'Research chambers with connecting corridors' if case=='laboratory' else 'An open survival arena',19)
            intent={'genre':'adventure','control':'top_down','gameplay':config.model_dump(),'requirements':[]};qa=composition_qa
            save(directory/'spec.json',ir.model_dump())
        elif case=='easy':
            d=runner.fixture_design('A forgiving easy woodland runner with gentle jumps and gradual progression');ir=runner.construct(d,'Easy comparison',7);intent={'requirements':[]};qa=runner_qa
            save(directory/'spec.json',ir.model_dump())
        else:
            ir,intent,compatibility,adapter=prepare(case);save(directory/'compatibility.json',compatibility)
            if ir is None:
                results.append({'case':case,'status':'BLOCKED','issues':compatibility['issues']});continue
            qa=boss_qa if ir.genre=='platformer' and ir.boss else platformer_qa if ir.genre=='platformer' else adventure_qa if ir.genre=='adventure' else runner_qa
        report=qa('http://127.0.0.1:5173/studio?example=forest',directory,ir.model_dump())
        semantic=fidelity(ir,intent,report);save(directory/'semantic_requirement_report.json',semantic)
        result={'case':case,'runtime':report['overall'],'passed':sum(c['passed'] for c in report['checks']),'failed':[c for c in report['checks'] if not c['passed']],'semantic':semantic['overall']}
        results.append(result);save(OUT/'browser-results.json',results);print(json.dumps(result),flush=True)
    save(OUT/'browser-results.json',results)

if __name__=='__main__':main()
