"""API lifecycle unit tests use explicit browser stubs; real evidence lives in docs/evidence."""
import pytest
from fastapi.testclient import TestClient
from main import app
from routes import platformer


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('AETHER_DB_PATH',str(tmp_path/'jobs.db'))
    monkeypatch.setenv('AETHER_ARTIFACTS_DIR',str(tmp_path/'artifacts'))
    with TestClient(app) as value:
        yield value


def submit(client,prompt='Peaceful forest with crystals and double jump'):
    result=client.post('/api/v2/games',json={'prompt':prompt,'mode':'fixture'})
    assert result.status_code==202
    return result.json()['game_id']


def test_persisted_fixture_and_unavailable_qa(client,monkeypatch):
    monkeypatch.setattr(platformer,'browser_report',lambda *args:{'overall':'UNAVAILABLE','checks':[],'scope':'Unit test stub: browser unavailable'})
    gid=submit(client)
    report=client.get(f'/api/v2/games/{gid}').json()
    assert report['job']['status']=='READY_WITH_WARNINGS'
    assert report['artifacts']['provider.json']['live'] is False
    assert report['artifacts']['asset_validation.json']['overall']=='PASS'
    assert report['artifacts']['qa_report.json']['overall']=='UNAVAILABLE'
    spec=client.get(f'/api/v2/games/{gid}/spec').json()
    assert spec['genre']=='platformer' and 'double_jump' in spec['player']['abilities']
    assert report['events'][0]['stage']=='QUEUED'
    assert client.get('/api/v2/games/not-found').status_code==404
    assert client.post('/api/v2/games',json={'prompt':'          ','mode':'fixture'}).status_code==422
    assert client.post('/api/v2/games',json={'prompt':'A forest platformer','mode':'pretend'}).status_code==422


def test_targeted_route_repair_preserves_failure_evidence(client,monkeypatch):
    reports=iter([
        {'overall':'FAIL','checks':[{'id':'mandatory_route_edges','passed':False,'critical':True,'category':'level_layout'}]},
        {'overall':'PASS','checks':[{'id':'mandatory_route_edges','passed':True,'critical':True,'category':'level_layout'}]},
    ])
    monkeypatch.setattr(platformer,'browser_report',lambda *args:next(reports))
    gid=submit(client,'Challenging precision tower with double jump');result=client.get(f'/api/v2/games/{gid}').json()
    assert result['job']['status']=='READY'
    artifacts=result['artifacts']
    assert artifacts['qa_report_initial.json']['overall']=='FAIL'
    assert artifacts['qa_report.json']['overall']=='PASS'
    changes=artifacts['repair_report.json']['attempts']
    assert len(changes)==1 and changes[0]['category']=='level_layout'
    assert changes[0]['before']['platforms']!=changes[0]['after']['platforms']
    assert any(e['stage']=='REPAIRING' for e in result['events'])


def test_runtime_defects_are_not_treated_as_balancing(client,monkeypatch):
    monkeypatch.setattr(platformer,'browser_report',lambda *args:{'overall':'FAIL','checks':[{'id':'no_runtime_exceptions','passed':False,'category':'runtime','critical':True}]})
    gid=submit(client);result=client.get(f'/api/v2/games/{gid}').json()
    assert result['job']['status']=='FAILED'
    assert not result['artifacts']['repair_report.json']['attempts']
    assert result['artifacts']['diagnosis.json']['failures'][0]['subsystem']=='runtime'


def test_reverify_retains_initial_report_and_is_bounded(client,monkeypatch):
    monkeypatch.setattr(platformer,'browser_report',lambda *args:{'overall':'PASS','checks':[{'id':'test_stub','passed':True}]})
    gid=submit(client)
    for _ in range(3):assert client.post(f'/api/v2/games/{gid}/verify').status_code==202
    assert client.post(f'/api/v2/games/{gid}/verify').status_code==409
    artifacts=client.get(f'/api/v2/games/{gid}').json()['artifacts']
    assert 'qa_report_initial.json' in artifacts and 'qa_retest_3.json' in artifacts
