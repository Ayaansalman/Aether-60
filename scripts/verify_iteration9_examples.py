"""Representative offline examples, each using the existing family QA adapter."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'aether-backend'))
from services import adventure,platformer,runner
from services.boss_qa import run_browser_qa as boss_qa
from services.adventure_qa import run_browser_qa as adventure_qa
from services.runner_qa import run_browser_qa as runner_qa
from tests.test_iteration7 import A,B
cases=[('boss',A),('biomes',B),('easy-runner','Create an easy endless forest runner with a woodland creature, forgiving jumps over spikes and gaps, and stable speed.'),('extreme-runner','Create an extreme endless industrial factory runner with a robot, spikes gaps and laser machinery, gradual acceleration and precision jumps.')]
for name,prompt in cases:
    if len(sys.argv)>1 and name not in sys.argv[1:]:continue
    out=ROOT/'docs/evidence/iteration9'/name;out.mkdir(parents=True,exist_ok=True)
    if name=='boss':
        d=platformer.fixture_design(prompt);platformer.enforce_explicit_requirements(d,prompt);ir=platformer.construct(d,prompt,7);qa=boss_qa
    elif name=='biomes':d=adventure.fixture_design(prompt);ir=adventure.construct(d,prompt,7);qa=adventure_qa
    else:d,_=runner.plan(prompt,'fixture');ir=runner.construct(d,prompt,7);qa=runner_qa
    (out/'design.json').write_text(d.model_dump_json(indent=2),encoding='utf-8');(out/'spec.json').write_text(ir.model_dump_json(indent=2),encoding='utf-8')
    report=qa('http://localhost:5173/studio?example=forest',out,ir.model_dump())
    print(name,report['overall'],len(report['checks']),[(c['id'],c['details']) for c in report['checks'] if not c['passed']],flush=True)
