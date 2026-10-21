"""Focused deterministic acceptance; optional single-case live Gemini verification."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'aether-backend'))
from dotenv import load_dotenv
from schemas.platformer import GameDesign, LevelDesign, GoalDesign, InteractionDesign, Motion, Entity, PlatformerIR
from services.platformer import plan, fixture_design, enforce_explicit_requirements, construct, validate_route
from services.platformer_qa import run_browser_qa
from services.capabilities import requirement_evidence

PROMPTS={
    'combat':'Create a forest platformer where I must defeat creatures guarding an ancient temple.',
    'factory':'Create a factory platformer where I must activate switches to open security doors while avoiding machinery.',
    'ice':'Create a difficult ice platformer with slippery terrain, falling hazards, and ranged enemies.',
    'mixed':'Deterministic two-level component integration fixture: pressure plates, projectile switches, armored turrets, ambushers, vertical platforms and campaign defeat objectives.',
    'timers':'A peaceful forest platformer. Survive for 2 seconds and reach the exit within 45 seconds.',
    'deadline':'A typed short-path runtime fixture with an achievable two-second deadline, tested for both expiry and early completion.',
}


def mixed_design():
    design=fixture_design('Forest platformer where I must defeat creatures')
    design.difficulty='relaxed';design.level_count=2
    first=[section.model_copy(deep=True) for section in design.sections[:5]]
    second=[section.model_copy(deep=True) for section in design.sections[:6]]
    for i,section in enumerate(first):
        section.enemies=i==1;section.encounter='patrol';section.hazards=False
    for i,section in enumerate(second):
        section.enemies=i in (1,3,5);section.encounter={1:'turret',3:'ambusher',5:'shooter'}.get(i,'patrol')
        section.ai.health=2 if i==1 else 1
        section.hazards=False;section.length=8
    design.levels=[
        LevelDesign(title='Pressure passage',sections=first,player_attack='stomp',interactions=[InteractionDesign(trigger='pressure',section=0,door_section=2)],objectives=[GoalDesign(kind='activate')]),
        LevelDesign(title='Security summit',sections=second,player_attack='projectile',moving_platforms=True,
                    platform_motion=Motion(axis='vertical',pattern='ping_pong',distance=36,period_ms=3000),
                    interactions=[InteractionDesign(trigger='projectile',section=0,door_section=2)],objectives=[GoalDesign(kind='defeat'),GoalDesign(kind='activate')]),
    ]
    design.campaign_objectives=[GoalDesign(kind='defeat')]
    return GameDesign.model_validate(design.model_dump())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',choices=[*PROMPTS,'all'],default='all')
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--saved-design',action='store_true')
    parser.add_argument('--url',default='http://127.0.0.1:5173/studio?example=forest')
    args=parser.parse_args()
    if args.live and args.case in ('all','mixed','deadline'): parser.error('Live verification requires one natural-language case')
    load_dotenv(ROOT/'aether-backend/.env')
    summaries=[]
    for case in PROMPTS if args.case=='all' else [args.case]:
        directory=ROOT/'docs/evidence/iteration4'/('live-'+case if args.live else case)
        directory.mkdir(parents=True,exist_ok=True)
        def save(name,value): (directory/name).write_text(json.dumps(value,indent=2),encoding='utf-8')
        if args.saved_design:
            design=GameDesign.model_validate_json((directory/'model_design.json').read_text(encoding='utf-8'))
            provenance={'provider':'saved_design_rebuild','live':False}
        elif case=='mixed': design,provenance=mixed_design(),{'provider':'typed_integration_fixture','live':False}
        elif case=='deadline': design,provenance=fixture_design('Peaceful forest within 2 seconds'),{'provider':'typed_short_path_timer_fixture','live':False}
        else:
            design,provenance=plan(PROMPTS[case],'live' if args.live else 'fixture')
        if not args.saved_design:
            save('model_design.json',design.model_dump());save('provider.json',provenance)
        guard={} if case in ('mixed','deadline') else enforce_explicit_requirements(design,PROMPTS[case])
        ir=construct(design,PROMPTS[case],seed=4242)
        if case=='deadline':
            ir.platforms=ir.platforms[:1]
            ir.entities=[Entity(id='L1_exit',kind='exit',x=190,y=ir.platforms[0].y*36-36,platform=0)]
            ir.objective={'type':'reach_exit','required':0,'total':0};ir.width=960
            ir=PlatformerIR.model_validate(ir.model_dump())
        validation=validate_route(ir)
        save('generation.json',{'prompt':PROMPTS[case],'provenance':provenance,'guard':guard,'design':design.model_dump()})
        save('spec.json',ir.model_dump());save('validation.json',validation)
        assert validation['overall']=='PASS', validation
        report=run_browser_qa(args.url,directory/'qa',fixture=ir.model_dump())
        save('requirements.json',requirement_evidence(ir,PROMPTS[case],design.unsupported,qa=report))
        summary={'case':case,'overall':report['overall'],'checks':len(report['checks']),'failures':[c for c in report['checks'] if not c['passed']]}
        summaries.append(summary);print(json.dumps(summary),flush=True)
    return 0 if all(result['overall']=='PASS' for result in summaries) else 1


if __name__=='__main__': raise SystemExit(main())
