import json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from schemas.runner import RunnerDesign
from services import runner
from services.semantic_intent import interpret,fidelity
from services.game_factory import parse_ir
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from prepare_iteration8 import PROMPTS

@pytest.mark.parametrize('key',PROMPTS)
def test_acceptance_roundtrip(key):
    prompt=PROMPTS[key];intent,_=interpret(prompt,'fixture');design,_=runner.plan(prompt,'fixture',intent.model_dump());ir=runner.construct(design,prompt,7)
    assert parse_ir(json.loads(ir.model_dump_json()))==ir
    assert fidelity(ir,intent.model_dump())['overall']=='PASS'
    assert ir.difficulty==('easy' if key in 'AC' else 'extreme')
    assert ir.theme==dict(A='forest',B='factory',C='sky',D='ice')[key]
    assert ir.mode==('ground' if key in 'AB' else 'flap')

def test_model_tuning_and_intent_survive(monkeypatch):
    from providers import factory
    class Provider:
        def complete(self,system,prompt):
            assert 'precision' in system and 'recovery' in system
            return SimpleNamespace(text=json.dumps(dict(mode='ground',difficulty='easy',speed=365,max_speed=470,challenge=dict(patterns=['rhythm','escalation'],recovery=.17,precision=.73))),model='stub')
    monkeypatch.setattr(factory,'get_provider',lambda:Provider())
    d,_=runner.plan('A hard industrial runner','live',{'arcade':{'difficulty':'hard','theme':'factory','exclusions':['laser']}})
    ir=runner.construct(d,'prompt',8)
    assert ir.speed==365 and ir.challenge.recovery==.17 and ir.challenge.patterns==['rhythm','escalation']
    assert ir.theme=='factory' and ir.difficulty=='hard' and 'laser' not in ir.obstacles
    assert fidelity(ir,{'arcade':{'difficulty':'easy'}})['overall']=='FAIL'

def test_profiles_stable_and_validation():
    assert RunnerDesign(difficulty='extreme',progression='stable').acceleration==0
    assert RunnerDesign(difficulty='extreme',challenge={'patterns':['mixed']}).challenge.recovery==.1
    for kwargs in [dict(mode='flap',exclusions=['gap']),dict(mode='flap',gap_height=96,flap_impulse=360,gravity=900),dict(challenge={'patterns':['alternating']}),dict(exclusions=['spike','gap','laser']),dict(challenge={'precision':.99})]:
        with pytest.raises(ValidationError):RunnerDesign(**kwargs)

@pytest.mark.parametrize('key',PROMPTS)
def test_real_api_pipeline(tmp_path,monkeypatch,key):
    from fastapi.testclient import TestClient
    from main import app
    from routes import platformer as route
    monkeypatch.setenv('AETHER_DB_PATH',str(tmp_path/'jobs.db'));monkeypatch.setenv('AETHER_ARTIFACTS_DIR',str(tmp_path/'artifacts'))
    monkeypatch.setattr(route,'browser_report',lambda *a:{'overall':'PASS','checks':[{'id':'runner_input','passed':True}]})
    with TestClient(app) as client:
        gid=client.post('/api/v2/games',json={'prompt':PROMPTS[key],'mode':'fixture','seed':7}).json()['game_id']
        result=client.get('/api/v2/games/'+gid).json()
        assert result['job']['status']=='READY'
        spec=client.get('/api/v2/games/'+gid+'/spec').json()
        assert spec['difficulty']==('easy' if key in 'AC' else 'extreme') and spec['challenge']['patterns']
