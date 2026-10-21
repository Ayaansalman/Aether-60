"""Bounded acceptance: actual Phaser runtime, optional single live design request.

The local fixture is intercepted at the preview's normal JSON boundary. Positions
are controlled for route edges/objectives; this is not an autonomous playthrough.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'aether-backend'))
from dotenv import load_dotenv
from services.platformer import plan, enforce_explicit_requirements, construct, validate_route
from services.platformer_qa import run_browser_qa
from services.capabilities import requirement_evidence

PROMPT = ('Create a three-level ice platformer. The first level introduces slippery terrain, '
          'the second introduces falling icicles, and the final level combines both mechanics with difficult platforming.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Use the configured provider; never fall back to fixtures')
    parser.add_argument('--saved-design', action='store_true', help='Rebuild the saved model design without another provider request')
    parser.add_argument('--case', choices=['ice', 'factory'], default='ice')
    parser.add_argument('--url', default='http://127.0.0.1:5173/studio?example=ice')
    args = parser.parse_args()
    prompt = PROMPT if args.case == 'ice' else 'Create two levels of industrial platforming with robot enemies, moving platforms, dangerous machinery, collectible crystals, checkpoints and dash.'
    load_dotenv(ROOT / 'aether-backend/.env')
    mode = 'live' if args.live else 'fixture'
    directory = ROOT / 'docs/evidence/iteration3' / (mode if args.case == 'ice' else mode + '-factory')
    directory.mkdir(parents=True, exist_ok=True)
    def save(name, data):
        (directory / name).write_text(json.dumps(data, indent=2), encoding='utf-8')
    try:
        if args.saved_design:
            from schemas.platformer import GameDesign
            design = GameDesign.model_validate_json((directory / 'model_design.json').read_text(encoding='utf-8'))
            provenance = {'provider': 'saved_design_rebuild', 'live': False, 'original_source': mode}
        else:
            design, provenance = plan(prompt, mode)
    except Exception as exc:
        save('provider_failure.json', {'type': type(exc).__name__, 'reason': 'Provider request failed; no fixture fallback was used.'})
        raise
    if not args.saved_design:
        save('model_design.json', design.model_dump())
        save('provider.json', provenance)
    guard = enforce_explicit_requirements(design, prompt)
    ir = construct(design, prompt, 314159)
    save('generation.json', {'prompt': prompt, 'provider': provenance, 'guard': guard, 'design': design.model_dump()})
    save('spec.json', ir.model_dump())
    validation = validate_route(ir)
    save('validation.json', validation)
    assert validation['overall'] == 'PASS', validation
    assert len(ir.levels) == (3 if args.case == 'ice' else 2)
    if args.case == 'ice':
        assert [level.slippery for level in ir.levels] == [True, False, True]
        assert [any(e.kind == 'icicle' for e in level.entities) for level in ir.levels] == [False, True, True]
    assert len({tuple((p.x,p.y,p.width) for p in level.platforms) for level in ir.levels}) == len(ir.levels)
    report = run_browser_qa(args.url, directory / 'qa', fixture=ir.model_dump())
    save('requirement_report.json', requirement_evidence(ir, prompt, design.unsupported, qa=report))
    print(json.dumps({'mode': mode, 'validation': validation['overall'], 'runtime': report['overall'],
                      'checks': len(report['checks']), 'failures': [c for c in report['checks'] if not c['passed']]}))
    return 0 if report['overall'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
