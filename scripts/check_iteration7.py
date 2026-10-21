"""Reproduce focused acceptance browser checks without model calls."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from tests.test_iteration7 import A,B,C,D
from services import platformer,adventure,runner
from services.boss_qa import run_browser_qa as boss_qa
from services.adventure_qa import run_browser_qa as adventure_qa
from services.runner_qa import run_browser_qa as runner_qa
out=ROOT/'docs/evidence/iteration7';out.mkdir(parents=True,exist_ok=True)
results={}
for name,prompt in [('A',A),('B',B),('C',C),('D',D)]:
    if len(sys.argv)>1 and name not in sys.argv[1:]:continue
    directory=out/name;directory.mkdir(exist_ok=True)
    if name=='A':
        d=platformer.fixture_design(prompt);platformer.enforce_explicit_requirements(d,prompt);ir=platformer.construct(d,prompt,7);qa=boss_qa
    elif name=='B':d=adventure.fixture_design(prompt);ir=adventure.construct(d,prompt,7);qa=adventure_qa
    else:d,_=runner.plan(prompt,'fixture');ir=runner.construct(d,prompt,7);qa=runner_qa
    (directory/'design.json').write_text(d.model_dump_json(indent=2),encoding='utf-8');(directory/'spec.json').write_text(ir.model_dump_json(indent=2),encoding='utf-8')
    report=qa('http://localhost:5173/studio?example=forest',directory,ir.model_dump());results[name]=report['overall']
    print(name,report['overall'],[(c['id'],c['details']) for c in report['checks'] if not c['passed']],flush=True)
(out/'summary.json').write_text(json.dumps(results,indent=2));print(results)
