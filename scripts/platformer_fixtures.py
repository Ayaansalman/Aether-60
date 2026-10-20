"""Regenerate deterministic fixture specifications. No model claims or calls."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'aether-backend'))
from services.platformer import fixture_design, construct, validate_route, enforce_explicit_requirements
from trace_iteration2 import PROMPTS as ITERATION_PROMPTS

PROMPTS={
    'forest':'A magical forest platformer where I collect crystals, avoid monsters, double jump across ruins and reach an ancient shrine.',
    'industrial':'An industrial platformer with moving machinery, dangerous obstacles, robot enemies, dash and checkpoints.',
    'tower':'A challenging precision jumping platformer with moving platforms, double jump and an ascent to the top of a tower.',
    'peaceful':'A peaceful easy forest platformer with no enemies, no hazards, crystals and checkpoints.',
}
PROMPTS.update(forest=ITERATION_PROMPTS['forest'], industrial=ITERATION_PROMPTS['factory'], ice=ITERATION_PROMPTS['ice'])

if __name__=='__main__':
    dest=ROOT/'aether-frontend/public/fixtures';dest.mkdir(exist_ok=True)
    evidence=[]
    for key,prompt in PROMPTS.items():
        design=fixture_design(prompt);enforce_explicit_requirements(design,prompt);ir=construct(design,prompt);report=validate_route(ir)
        (dest/f'{key}.json').write_text(ir.model_dump_json(indent=2),encoding='utf-8')
        evidence.append({'id':key,'prompt':prompt,'source':'fixture','live':False,'design':design.model_dump(),'validation':report})
        print(key,ir.seed,len(ir.platforms),report['overall'])
    (ROOT/'docs/platformer-fixture-results.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
