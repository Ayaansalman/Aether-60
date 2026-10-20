"""Capture actual parser/planner/build contracts; never substitutes fixtures for live calls."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'aether-backend'))
from services.platformer import plan, construct, enforce_explicit_requirements, validate_route

PROMPTS = {
    'forest': 'Create a colorful forest platformer with collectible crystals, patrolling creatures, and a glowing shrine at the end.',
    'factory': 'Create an industrial platformer with robotic enemies, moving platforms, dangerous machinery, and checkpoints across multiple stages.',
    'ice': 'Create a frozen underground platformer with slippery terrain, falling icicles, collectible relics, and a flashing light at the exit.',
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', default='before')
    parser.add_argument('--mode', choices=['fixture', 'live'], default='fixture')
    args = parser.parse_args()
    directory = ROOT / 'docs/evidence/iteration2' / args.phase / args.mode
    directory.mkdir(parents=True, exist_ok=True)
    for name, prompt in PROMPTS.items():
        result = {'prompt': prompt, 'mode': args.mode}
        try:
            design, provenance = plan(prompt, args.mode)
            result.update(model_design=design.model_dump(), provider=provenance)
            result['requirements'] = enforce_explicit_requirements(design, prompt)
            result['design'] = design.model_dump()
            ir = construct(design, prompt)
            result.update(game_ir=ir.model_dump(), validation=validate_route(ir))
        except Exception as exc:
            result['error'] = {'type': type(exc).__name__, 'code': getattr(exc, 'code', None)}
        (directory / f'{name}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(name, result.get('error', result.get('validation', {}).get('overall')), flush=True)
