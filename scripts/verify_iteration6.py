"""Rebuild deterministic examples and exercise rendered acceptance cases.

No model calls. --live uses the API for exactly two real planning calls instead.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'aether-backend'))
from services.adventure import fixture_design, construct, validate_world
from services.adventure_qa import run_browser_qa
from tests.test_iteration6 import HERBALIST, CRYPT


def request(api,path,data=None):
    req=urllib.request.Request(api+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--case',choices=['village','crypt'])
    parser.add_argument('--api',default='http://127.0.0.1:8002')
    parser.add_argument('--frontend',default='http://localhost:5175')
    parser.add_argument('--fixtures-only',action='store_true')
    args=parser.parse_args()
    out=ROOT/'docs/evidence/iteration6';out.mkdir(parents=True,exist_ok=True)
    failures=[]
    for name,prompt in [('village',HERBALIST),('crypt',CRYPT)]:
        if args.case and args.case!=name:continue
        if args.live:
            gid=request(args.api,'/api/v2/games',{'prompt':prompt,'mode':'live','seed':42})['game_id']
            deadline=time.monotonic()+300
            while time.monotonic()<deadline:
                report=request(args.api,f'/api/v2/games/{gid}')
                if report['job']['status'] in ('READY','READY_WITH_WARNINGS','FAILED'):break
                time.sleep(2)
            (out/f'live-{name}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(name,report['job']['status'],report['job'].get('qa_summary'),flush=True)
            if report['job']['status'] not in ('READY','READY_WITH_WARNINGS'):failures.append(name)
        else:
            spec=construct(fixture_design(prompt),prompt,42)
            validation=validate_world(spec)
            assert validation['overall']=='PASS',validation
            data=spec.model_dump()
            (ROOT/f'aether-frontend/public/fixtures/{name}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
            (out/f'{name}-validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
            if not args.fixtures_only:
                # The route supplies our exact acceptance IR to the existing preview.
                report=run_browser_qa(args.frontend+'/studio?example='+name,out/name,fixture=data)
                print(name,report['overall'],len(report['checks']),flush=True)
                if report['overall']!='PASS':failures.append(name)
    sys.exit(bool(failures))
