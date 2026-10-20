"""Run all three exact prompts through the persisted API and real browser QA."""
import argparse
import json
import shutil
import time
from pathlib import Path
import httpx
from trace_iteration2 import PROMPTS, ROOT

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['fixture','live'],default='fixture')
    parser.add_argument('--reuse',type=Path)
    args=parser.parse_args()
    dest=ROOT/'docs/evidence/iteration2/after'/args.mode
    dest.mkdir(parents=True,exist_ok=True)
    with httpx.Client(timeout=20) as client:
        ids=json.loads(args.reuse.read_text()) if args.reuse else {}
        if not ids:
            for name,prompt in PROMPTS.items():
                response=client.post('http://127.0.0.1:8000/api/v2/games',json={'prompt':prompt,'mode':args.mode})
                response.raise_for_status();ids[name]=response.json()['game_id']
            (dest/'job-ids.json').write_text(json.dumps(ids,indent=2),encoding='utf-8')
        pending=set(ids);last={};summary={}
        deadline=time.monotonic()+1200
        while pending and time.monotonic()<deadline:
            for name in list(pending):
                response=client.get('http://127.0.0.1:8000/api/v2/games/'+ids[name]);response.raise_for_status()
                data=response.json();status=data['job']['status']
                if status!=last.get(name):print(name,status,flush=True);last[name]=status
                if status in ('READY','READY_WITH_WARNINGS','FAILED'):
                    (dest/f'{name}-job.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
                    reports=[value for key,value in data['artifacts'].items() if key=='qa_report.json' or key.startswith('qa_retest_')]
                    qa=reports[-1] if reports else {}
                    summary[name]={'game_id':ids[name],'status':status,'qa':qa.get('overall'),
                                   'failed':[c['id'] for c in qa.get('checks',[]) if not c['passed']],
                                   'requirements':data['artifacts'].get('requirement_report.json')}
                    source=ROOT/'aether-backend/artifacts'/ids[name]
                    for screenshot in source.rglob('*.png'):
                        target=dest/name/screenshot.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copyfile(screenshot,target)
                    print(name,json.dumps({k:v for k,v in summary[name].items() if k!='requirements'}),flush=True)
                    pending.remove(name)
            if pending:time.sleep(2)
        (dest/'summary.json').write_text(json.dumps({'results':summary,'unfinished':sorted(pending)},indent=2),encoding='utf-8')
