"""V2 generation API: persisted jobs, honest stage events and bounded layout repair."""
import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from services import job_store, event_store
from services.orchestrator import get_artifacts_dir
from services.platformer import plan, construct, validate_route, enforce_explicit_requirements, validate_assets
from services.capabilities import extract_requirements, requirement_evidence

router = APIRouter()
_worker = asyncio.Lock()


def browser_report(game_url, directory, genre="platformer"):
    try:
        proc = subprocess.run([sys.executable,"-m",("services.boss_qa" if genre=="boss" else "services.runner_qa" if genre=="runner" else "services.adventure_qa" if genre=="adventure" else "services.platformer_qa"),game_url,str(directory)],
            cwd=str(Path(__file__).resolve().parents[1]),capture_output=True,text=True,timeout=240)
        return json.loads(proc.stdout.strip())
    except Exception as exc:
        return {"overall":"UNAVAILABLE","checks":[],"error":type(exc).__name__,"scope":"Browser verification did not complete; no runtime success is claimed."}


class Generate(BaseModel):
    prompt: str = Field(min_length=10, max_length=3000)
    mode: Literal["live", "fixture"] = "live"
    seed: int | None = Field(default=None, ge=0, le=4294967295)


def save(gid, name, data):
    directory = get_artifacts_dir() / gid
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(data, indent=2), encoding="utf-8")


async def run(gid: str, request: Generate):
    async with _worker:
        started = time.monotonic()
        artifacts = []

        def stage(name, detail, result="SUCCESS"):
            job_store.update_job(gid, status=name, stage=name)
            event_store.add_event(gid, stage=name, result=result, detail=detail,
                rationale=f"Elapsed {time.monotonic()-started:.2f}s; " + ("language model" if name=="PLANNING" and request.mode=="live" else "deterministic service"))

        def artifact(name, value):
            save(gid, name, value)
            if name not in artifacts:
                artifacts.append(name)
            job_store.update_job(gid, artifact_paths=artifacts)

        try:
            from services.semantic_intent import interpret
            stage('PLANNING','Interpreting central loop, controls and constraints','START')
            intent,intent_provider=await asyncio.to_thread(interpret,request.prompt,request.mode)
            artifact('semantic_intent.json', {**intent.model_dump(),'provenance':intent_provider})
            if intent.genre=='unsupported': raise ValueError('Requested game family is unsupported; see semantic_intent.json')
            if intent.genre=='runner':
                from services.runner import run_runner
                await run_runner(gid,request,artifact,stage,browser_report,intent.model_dump())
                return
            if intent.genre=="adventure":
                from services.adventure_pipeline import run_adventure
                await run_adventure(gid,request,artifact,stage,browser_report,intent.model_dump())
                return
            artifact("game_intent.json", {"original_prompt": request.prompt, "requirements": extract_requirements(request.prompt),
                "scope": "Explicit phrases; model interpretation follows. Unrecognized language is not certified."})
            stage("PLANNING", "Interpreting prompt with Gemini" if request.mode=="live" else "Building explicitly labeled offline fixture", "START")
            design, provenance = await asyncio.to_thread(plan, request.prompt, request.mode,intent.model_dump())
            artifact("model_design.json", design.model_dump())
            requirements = enforce_explicit_requirements(design, request.prompt)
            artifact("requirement_report.json", requirements)
            artifact("game_intent.json", {"original_prompt":request.prompt,"genre":design.genre,"setting":design.theme,
                "gameplay": {"objectives":[goal.model_dump() for goal in design.objectives],
                    "campaign_objectives":[goal.model_dump() for goal in design.campaign_objectives],
                    "interactions":[item.model_dump() for item in design.interactions],"player_attack":design.player_attack},
                "level_count": design.level_count, "progression": [level.model_dump(exclude_none=True) for level in design.levels],
                "requested_mechanics":requirements['requirements'],"model_requests":[f.model_dump() for f in design.requested_features],"unsupported":design.unsupported,"interpretation_source":provenance})
            artifact("game_design.json", design.model_dump())
            artifact("provider.json", provenance)
            job_store.update_job(gid, model_id=provenance['model'] or "fixture", limitations=design.unsupported + [note for note in design.design_notes if 'approximat' in note.lower()])
            stage("DESIGNING", "Validated typed design; composing sections and registered mechanics")
            ir = construct(design, request.prompt, request.seed)
            stage("VALIDATING_SPEC", "Checking jump trajectories, landing margins and objective consistency")
            validation = validate_route(ir)
            repairs = []
            for attempt in range(2):
                if validation['overall'] == 'PASS':
                    break
                before = design.model_dump()
                failed_validation = validation
                for section in [*design.sections, *(section for level in design.levels for section in level.sections)]:
                    section.gap = max(1, section.gap - 1)
                    section.elevation = min(section.elevation, 1)
                stage("REPAIRING", "Reducing unreachable gaps and rises; rebuilding from the same seed")
                ir = construct(design, request.prompt, ir.seed)
                validation = validate_route(ir)
                repairs.append({"attempt":attempt+1,"category":"level_layout","evidence":failed_validation,"before":before,"after":design.model_dump(),"validation":validation})
            artifact("repair_report.json", {"attempts":repairs,"maximum":2})
            artifact("final_design.json", design.model_dump())
            artifact("validation.json", validation)
            if validation['overall'] != 'PASS':
                raise ValueError("Route remains unreachable after bounded layout repair")
            artifact("game_ir_v2.json", ir.model_dump())
            coverage = requirement_evidence(ir, request.prompt, design.unsupported)
            artifact("requirement_report.json", {**requirements, **coverage})
            if coverage['overall'] == 'FAIL':
                raise ValueError("Requested supported capabilities are missing from the constructed specification. Inspect requirement_report.json.")
            public = Path(__file__).resolve().parents[2]/"aether-frontend/public"
            manifest = json.loads((public/"assets/registry.json").read_text())
            artifact("asset_manifest.json", manifest)
            asset_validation = validate_assets(manifest, public)
            artifact("asset_validation.json", asset_validation)
            if asset_validation['overall'] != 'PASS':
                raise ValueError("Registered artwork is missing or has an invalid checksum. Inspect asset_validation.json.")
            game_url = os.getenv("AETHER_FRONTEND_URL", "http://localhost:5173").rstrip('/') + f"/studio/play/{gid}"
            job_store.update_job(gid, spec_json=ir.model_dump_json(), game_url=game_url)
            artifact("build_manifest.json", {"runtime":"Phaser 3 Arcade","genre":ir.genre,"schema_version":ir.schema_version,
                "seed":ir.seed,"game_url":game_url,"capabilities":[r['id'] for r in coverage['requirements'] if r.get('constructed')],
                "moving_platforms":design.moving_platforms,"level_count":len(ir.levels) or 1,"topology":design.topology,
                "exit_style":ir.exit_style,"exit_indicator":ir.exit_indicator})
            stage("BUILDING", "Runtime specification and asset dependencies persisted")
            stage("TESTING", "Running real Chromium gameplay checks", "START")
            # Subprocess timeout bounds QA, including browser startup and every route edge.
            report = await asyncio.to_thread(browser_report,game_url,get_artifacts_dir()/gid,"boss" if ir.boss else "platformer")
            artifact("qa_report_initial.json", report)
            while report['overall']=='FAIL' and len(repairs)<2:
                failed=[c for c in report['checks'] if not c['passed'] and c.get('critical',True)]
                if not failed or any(c['id']!='mandatory_route_edges' for c in failed):
                    break
                before=ir.model_dump()
                for section in [*design.sections, *(section for level in design.levels for section in level.sections)]:
                    section.gap=1;section.elevation=min(section.elevation,1)
                ir=construct(design,request.prompt,ir.seed)
                if ir.model_dump()==before:
                    break
                stage('REPAIRING','Browser evidence identified a level route failure; reducing only gaps and elevation')
                repaired_validation=validate_route(ir)
                if repaired_validation['overall']!='PASS':
                    break
                repairs.append({'attempt':len(repairs)+1,'category':'level_layout','evidence':failed,'before':before,'after':ir.model_dump()})
                artifact('repair_report.json',{'attempts':repairs,'maximum':2})
                save(gid,'game_ir_v2.json',ir.model_dump())
                save(gid,'final_design.json',design.model_dump())
                save(gid,'validation.json',repaired_validation)
                job_store.update_job(gid,spec_json=ir.model_dump_json())
                stage('TESTING',f'Retesting targeted route repair {len(repairs)}','START')
                report=await asyncio.to_thread(browser_report,game_url,get_artifacts_dir()/gid/f'repair-{len(repairs)}')
                artifact(f'qa_repair_{len(repairs)}.json',report)
            artifact('diagnosis.json',{'failures':[{'check':c['id'],'subsystem':c.get('category','runtime'),
                'action':'Needs developer; no arbitrary code or balancing patch applied' if c.get('category')!='level_layout' else 'See bounded route repair history'}
                for c in report['checks'] if not c['passed']], 'repairs_applied':len(repairs)})
            artifact("qa_report.json", report)
            coverage = requirement_evidence(ir, request.prompt, design.unsupported, report)
            artifact("requirement_report.json", {**requirements, **coverage})
            ir.requirements = coverage['requirements']
            artifact("game_ir_v2.json", ir.model_dump())
            job_store.update_job(gid, spec_json=ir.model_dump_json())
            job_store.update_job(gid, latest_qa_json=json.dumps(report), qa_summary={"passed":sum(c['passed'] for c in report['checks']),"failed":sum(not c['passed'] for c in report['checks']),"critical_failed":[c['id'] for c in report['checks'] if not c['passed'] and c.get('critical',True)]})
            from services.semantic_intent import fidelity
            semantic=fidelity(ir,intent.model_dump(),report)
            artifact('semantic_requirement_report.json',semantic)
            if report['overall']=='FAIL' or coverage['overall']=='FAIL' or semantic['overall']=='FAIL':
                final="FAILED"
                detail="Runtime QA failed; evidence recorded. Runtime/asset defects require a developer, not difficulty patches."
            else:
                final="READY" if report['overall']=='PASS' and coverage['overall']=='PASS' and semantic['overall']=='PASS' and not design.unsupported and not any("approximat" in n.lower() for n in design.design_notes) else "READY_WITH_WARNINGS"
                detail="Browser checks passed" if report['overall']=='PASS' else "Specification ready; browser QA unavailable. Runtime remains unverified."
            stage(final, detail)
            artifact("outcome.json", {"status":final,"elapsed_seconds":round(time.monotonic()-started,2),"visual_quality":"Requires human screenshot review; functional checks are not an aesthetic score."})
        except Exception as exc:
            # Never persist raw provider messages: upstream errors can echo credentials/request content.
            code = getattr(exc, 'code', 'GENERATION_FAILED')
            safe = str(exc)[:500] if isinstance(exc, ValueError) else f"{code}: {type(exc).__name__}. Check provider configuration or retry later."
            event_store.add_event(gid, stage="FAILED", result="FAILED", detail=safe)
            job_store.update_job(gid, status="FAILED", stage="FAILED", error_code=code)


@router.post("/games", status_code=202)
async def generate(request: Generate, background: BackgroundTasks):
    if not request.prompt.strip() or len(request.prompt.strip()) < 10:
        raise HTTPException(422, "Describe your game in at least 10 characters")
    gid = str(uuid.uuid4())
    job_store.create_job(gid, request.prompt.strip(), prompt_version="2.0")
    event_store.add_event(gid, stage="QUEUED", result="START", detail=f"Accepted {request.mode} generation request")
    background.add_task(run, gid, request)
    return {"game_id":gid,"status":"QUEUED"}


@router.get("/games/{gid}")
async def inspect(gid: str):
    job = job_store.get_job(gid)
    if not job or job['prompt_version'] != '2.0':
        raise HTTPException(404, "V2 game not found")
    artifacts = {}
    for name in job['artifact_paths']:
        # Paths are server-authored, but still confine reads to known JSON artifacts.
        if Path(name).name == name and name.endswith('.json'):
            path = get_artifacts_dir()/gid/name
            if path.is_file():
                artifacts[name] = json.loads(path.read_text(encoding='utf-8'))
    return {"job":{k:v for k,v in job.items() if k not in ('spec_json','latest_qa_json')},"events":event_store.get_events(gid),"artifacts":artifacts}


@router.get("/games/{gid}/spec")
async def spec(gid: str):
    job = job_store.get_job(gid)
    if not job or job['prompt_version'] != '2.0' or not job['spec_json']:
        raise HTTPException(404, "Specification not available yet")
    return json.loads(job['spec_json'])


async def reverify_job(gid: str):
    async with _worker:
        job=job_store.get_job(gid)
        paths=job['artifact_paths']
        attempt=1+sum(name.startswith('qa_retest_') for name in paths)
        genre=json.loads(job['spec_json']).get('genre','platformer')
        qa_genre='boss' if json.loads(job['spec_json']).get('boss') else genre
        report=await asyncio.to_thread(browser_report,job['game_url'],get_artifacts_dir()/gid/f'verification-{attempt}',qa_genre)
        name=f'qa_retest_{attempt}.json';save(gid,name,report);paths.append(name)
        from services.game_factory import parse_ir
        ir=parse_ir(json.loads(job['spec_json']))
        if genre=='adventure':
            from services import adventure
            save(gid,'asset_manifest.json',adventure.asset_manifest(ir.art))
            save(gid,'asset_validation.json',adventure.validate_assets())
            save(gid,'validation.json',adventure.validate_world(ir))
            coverage={'overall':'PASS' if report['overall']=='PASS' else 'UNVERIFIED', 'requirements':[dict(r,status='verified' if report['overall']=='PASS' else 'constructed_unverified') for r in ir.requirements]}
        elif genre=='runner':
            coverage={'overall':report['overall'],'requirements':[dict(r,status='verified' if report['overall']=='PASS' else 'constructed_unverified') for r in ir.requirements]}
        else:
            coverage=requirement_evidence(ir,job['prompt'],job['limitations'],report)
        previous=json.loads((get_artifacts_dir()/gid/'requirement_report.json').read_text(encoding='utf-8'))
        save(gid,'requirement_report.json',{**previous,**coverage})
        ir.requirements=coverage['requirements'];save(gid,'game_ir_v2.json',ir.model_dump())
        from services.semantic_intent import fidelity
        intent_path=get_artifacts_dir()/gid/'semantic_intent.json'
        semantic=fidelity(ir,json.loads(intent_path.read_text(encoding='utf-8')),report) if intent_path.is_file() else {'overall':'PASS'}
        if intent_path.is_file():
            save(gid,'semantic_requirement_report.json',semantic)
            if 'semantic_requirement_report.json' not in paths: paths.append('semantic_requirement_report.json')
        final='FAILED' if report['overall']=='FAIL' or coverage['overall']=='FAIL' or semantic['overall']=='FAIL' else 'READY' if report['overall']=='PASS' and coverage['overall']=='PASS' and semantic['overall']=='PASS' and not job['limitations'] else 'READY_WITH_WARNINGS'
        job_store.update_job(gid,status=final,stage=final,spec_json=ir.model_dump_json(),latest_qa_json=json.dumps(report),artifact_paths=paths,
            qa_summary={'passed':sum(c['passed'] for c in report['checks']),'failed':sum(not c['passed'] for c in report['checks']),
                'critical_failed':[c['id'] for c in report['checks'] if not c['passed'] and c.get('critical',True)]})
        event_store.add_event(gid,stage='TESTING',result='SUCCESS' if report['overall']=='PASS' else 'FAILED',
            detail=f"Runtime re-verification {attempt}: {report['overall']}. Original report preserved; no new model call.",attempt=attempt+1)
        save(gid,'outcome.json',{'status':final,'verification':attempt,'visual_quality':'Requires screenshot review; QA is functional evidence.'})


@router.post('/games/{gid}/verify',status_code=202)
async def reverify(gid: str,background: BackgroundTasks):
    job=job_store.get_job(gid)
    if not job or job['prompt_version']!='2.0' or not job['spec_json']:
        raise HTTPException(404,'A built V2 game is required')
    if job['status'] not in ('READY','READY_WITH_WARNINGS','FAILED'):
        raise HTTPException(409,'A job is already running')
    if sum(name.startswith('qa_retest_') for name in job['artifact_paths'])>=3:
        raise HTTPException(409,'Maximum three explicit re-verifications reached')
    job_store.update_job(gid,status='TESTING',stage='TESTING')
    event_store.add_event(gid,stage='TESTING',result='START',detail='Explicit browser re-verification requested; original evidence preserved.')
    background.add_task(reverify_job,gid)
    return {'game_id':gid,'status':'TESTING'}
