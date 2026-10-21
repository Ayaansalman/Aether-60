"""Generate the two milestone prompts through the real API; --live makes two provider calls."""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'aether-backend'))
from tests.test_adventure import VILLAGE,DUNGEON


def request(base,path,data=None):
    req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,
                               headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--api',default='http://127.0.0.1:8001')
    args=parser.parse_args();mode='live' if args.live else 'fixture';pending={}
    out=ROOT/'docs/evidence/iteration5'/mode;out.mkdir(parents=True,exist_ok=True)
    for name,prompt in [('village',VILLAGE),('dungeon',DUNGEON)]:
        gid=request(args.api,'/api/v2/games',{'prompt':prompt,'mode':mode,'seed':42})['game_id'];pending[name]=gid
        print(name,gid,flush=True)
    deadline=time.monotonic()+600;failed=False
    while pending and time.monotonic()<deadline:
        for name,gid in list(pending.items()):
            report=request(args.api,f'/api/v2/games/{gid}')
            if report['job']['status'] in ('READY','READY_WITH_WARNINGS','FAILED'):
                (out/(name+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
                print(name,report['job']['status'],report['job'].get('qa_summary'),flush=True)
                failed|=report['job']['status']=='FAILED';del pending[name]
        if pending:time.sleep(2)
    if pending:print('Timed out waiting for',pending)
    sys.exit(1 if failed or pending else 0)
