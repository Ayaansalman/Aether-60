import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from tests.test_iteration9 import A,design,semantic
from services import adventure
from services.composition_qa import run_browser_qa
out=ROOT/'docs/evidence/iteration9/fixture-A';out.mkdir(parents=True,exist_ok=True)
ir=adventure.construct(design(),A,7)
(out/'spec.json').write_text(ir.model_dump_json(indent=2),encoding='utf-8')
report=run_browser_qa('http://localhost:5173/studio?example=forest',out,ir.model_dump())
print(report['overall'],[(c['id'],c['details']) for c in report['checks'] if not c['passed']])
