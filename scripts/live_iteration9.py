"""Explicit, bounded live verification: one semantic call and one designer call per case, with at most one correction per boundary."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from tests.test_iteration9 import A,D
from services.semantic_intent import interpret,feasibility,fidelity
from services import adventure,platformer
from services.composition_qa import run_browser_qa as composition_qa
from services.platformer_qa import run_browser_qa as platformer_qa
case=sys.argv[1] if len(sys.argv)>1 else 'A';prompt={'A':A,'D':D}[case]
out=ROOT/'docs/evidence/iteration9'/('live-'+case);out.mkdir(parents=True,exist_ok=True)
def save(name,value):(out/name).write_text(json.dumps(value,indent=2),encoding='utf-8')
resume='--resume' in sys.argv
try:
    if resume:
        from services.semantic_intent import Intent
        captured=json.loads((out/'intent.json').read_text(encoding='utf-8'));intent=Intent.model_validate({k:v for k,v in captured.items() if k!='provenance'});provenance=captured['provenance']
    else:intent,provenance=interpret(prompt,'live')
except Exception as exc:
    if hasattr(exc,'attempts'):save('failed-validation.json',exc.attempts)
    raise
save('intent.json',{**intent.model_dump(),'provenance':provenance});print('Intent',case,intent.genre,intent.control,flush=True)
compatibility=feasibility(intent.model_dump());save('compatibility.json',compatibility)
if compatibility['overall']=='FAIL':raise ValueError('Capability compatibility failed')
if intent.genre=='adventure':
    d,source=adventure.plan(prompt,'live',lambda raw:save('model_design.json',raw),intent.model_dump());adventure.enforce_requirements(d,prompt)
    ir=adventure.construct(d,prompt,7);qa=composition_qa
else:
    if resume:
        from providers.factory import get_provider,set_custom_provider
        from types import SimpleNamespace
        real=get_provider();saved=json.loads((out/'model_design.json').read_text(encoding='utf-8'))
        class CapturedThenLive:
            calls=0
            def complete(self,system,user):
                self.calls+=1
                if self.calls==1:return SimpleNamespace(text=json.dumps(saved),model=provenance['model'],latency_ms=0,fallback_events=[])
                return real.complete(system,user)
        set_custom_provider(CapturedThenLive())
    d,source=platformer.plan(prompt,'live',intent.model_dump());save('corrected_model_design.json' if resume else 'model_design.json',d.model_dump());guard=platformer.enforce_explicit_requirements(d,prompt);save('guard.json',guard)
    ir=platformer.construct(d,prompt,7);qa=platformer_qa
save('provider.json',source);save('design.json',d.model_dump());save('spec.json',ir.model_dump())
preliminary=fidelity(ir,intent.model_dump());save('fidelity-before-runtime.json',preliminary)
print('Constructed',case,'fidelity',preliminary['overall'],flush=True)
if preliminary['overall']=='FAIL':raise ValueError('Semantic construction fidelity failed')
report=qa('http://localhost:5173/studio?example=forest',out,ir.model_dump());save('fidelity.json',fidelity(ir,intent.model_dump(),report))
print('Runtime',case,report['overall'],[(c['id'],c['details']) for c in report['checks'] if not c['passed']],flush=True)
