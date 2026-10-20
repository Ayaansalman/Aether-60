"""Collect real persisted evaluations; live and fixture runs stay explicitly separate.

Start backend and frontend first. Use --mode live to make four provider requests,
--mode fixture for deterministic offline tests, or --reuse <ids.json> to export existing jobs.
"""
import argparse
import json
import time
from pathlib import Path
import httpx
from platformer_fixtures import PROMPTS, ROOT


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['live','fixture'],default='fixture')
    parser.add_argument('--reuse',type=Path)
    parser.add_argument('--api',default='http://127.0.0.1:8000')
    args=parser.parse_args()
    dest=ROOT/'docs/evidence'/args.mode;dest.mkdir(parents=True,exist_ok=True)
    with httpx.Client(timeout=15) as client:
        if args.reuse:
            ids=json.loads(args.reuse.read_text())
        else:
            ids={}
            for name,prompt in PROMPTS.items():
                res=client.post(args.api+'/api/v2/games',json={'prompt':prompt,'mode':args.mode});res.raise_for_status()
                ids[name]=res.json()['game_id']
            (dest/'job-ids.json').write_text(json.dumps(ids,indent=2))
        deadline=time.monotonic()+900
        pending=set(ids);results={};last={}
        while pending and time.monotonic()<deadline:
            for name in list(pending):
                res=client.get(args.api+'/api/v2/games/'+ids[name]);res.raise_for_status();data=res.json()
                state=data['job']['status']
                if state!=last.get(name):print(name,state,flush=True);last[name]=state
                if state in ('READY','READY_WITH_WARNINGS','FAILED'):
                    (dest/f'{name}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
                    reports=[(key,value) for key,value in data['artifacts'].items() if key=='qa_report.json' or key.startswith('qa_retest_')]
                    report=reports[-1][1] if reports else {'overall':'NOT_RUN','checks':[]}
                    ir=data['artifacts'].get('game_ir_v2.json',{})
                    results[name]={'game_id':ids[name],'status':state,'source':data['artifacts'].get('provider.json'),
                        'title':ir.get('title'),'theme':ir.get('theme'),'seed':ir.get('seed'),
                        'sections':len([p for p in ir.get('platforms',[]) if not p['moving']]),
                        'moving_platforms':sum(p['moving'] for p in ir.get('platforms',[])),
                        'objective':ir.get('objective'),'abilities':ir.get('player',{}).get('abilities'),
                        'qa':report['overall'],'passed':sum(c['passed'] for c in report['checks']),
                        'failed':[c['id'] for c in report['checks'] if not c['passed']],
                        'limitations':data['job']['limitations']}
                    pending.remove(name)
            if pending:time.sleep(1)
        (dest/'summary.json').write_text(json.dumps({'mode':args.mode,'results':results,'unfinished':sorted(pending),
            'scope':'Browser checks use disclosed controlled state injection for objectives and isolated launches for route edges. Not an aesthetic score or full autonomous playthrough.'},indent=2),encoding='utf-8')
        print(json.dumps(results,indent=2))


if __name__=='__main__':main()
