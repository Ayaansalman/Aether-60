import json
from types import SimpleNamespace
from pathlib import Path
from routes.platformer import qa_player_url


def test_browser_qa_uses_separate_runtime_preserving_public_url_and_query():
    from services.qa_urls import playback_job_id
    assert qa_player_url('http://localhost:5173/studio/play/id?test=1')=='http://localhost:5173/studio/verify/id?test=1'
    assert qa_player_url('http://localhost:5173/studio?example=forest')=='http://localhost:5173/studio?example=forest'
    for route in ('play','verify'):
        assert playback_job_id(f'http://localhost:5173/studio/{route}/job-123?test=1#game')=='job-123'
    assert playback_job_id('http://localhost:5173/studio?example=forest') is None


def test_model_fallback_event_is_persisted_safely_and_scoped_to_its_job(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from providers import factory
    from providers.openai_compat import OpenAICompatProvider,reset_process_fallback_state
    from services import runner
    from routes import platformer as route
    reset_process_fallback_state()
    monkeypatch.setenv('AETHER_DB_PATH',str(tmp_path/'jobs.db'));monkeypatch.setenv('AETHER_ARTIFACTS_DIR',str(tmp_path/'artifacts'))
    transport=OpenAICompatProvider(base_url='https://example.invalid/v1',model_name='primary',fallbacks=['backup'],api_key='local-test')
    class Provider:
        calls=0
        def complete(self,*args):
            self.calls+=1
            if self.calls==1:transport._trigger_fallback('primary','network error: sensitive upstream response must not be persisted')
            value={'genre':'runner','control':'auto_jump','loop':'Jump over obstacles','requirements':[]} if self.calls%2 else runner.fixture_design('An easy forest runner').model_dump()
            return SimpleNamespace(text=json.dumps(value),model='backup',latency_ms=0,fallback_events=[])
    monkeypatch.setattr(factory,'get_provider',lambda:ProviderInstance)
    ProviderInstance=Provider()
    monkeypatch.setattr(route,'browser_report',lambda *args:{'overall':'PASS','checks':[{'id':'runner_input','passed':True}]})
    with TestClient(app) as client:
        first=client.post('/api/v2/games',json={'prompt':'An easy automatic forest runner','mode':'live'}).json()['game_id']
        result=client.get('/api/v2/games/'+first).json()
        assert result['job']['status']=='READY'
        switches=result['artifacts']['model_fallbacks.json']['events']
        assert switches[0]['to_model']=='backup' and switches[0]['reason']=='provider unavailable'
        assert any(e['stage']=='MODEL_FALLBACK' and 'primary → backup' in e['detail'] for e in result['events'])
        assert 'sensitive upstream' not in json.dumps(result)
        second=client.post('/api/v2/games',json={'prompt':'Another automatic forest runner','mode':'live'}).json()['game_id']
        assert 'model_fallbacks.json' not in client.get('/api/v2/games/'+second).json()['artifacts']
    reset_process_fallback_state()


def test_configured_fallback_models_keep_existing_primary_and_credentials():
    # Inspect names only, never return credential values in test diagnostics.
    from dotenv import dotenv_values
    config=dotenv_values(Path(__file__).resolve().parents[1]/'.env.example')
    assert config['MODEL_NAME']=='gemini-3.5-flash-lite'
    assert config['MODEL_FALLBACKS']=='gemini-3.5-flash,gemini-3.8-flash'


def test_api_failures_explain_recovery_without_echoing_upstream_secrets(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from services import semantic_intent
    from providers.base import ModelHttpError
    monkeypatch.setenv('AETHER_DB_PATH',str(tmp_path/'jobs.db'));monkeypatch.setenv('AETHER_ARTIFACTS_DIR',str(tmp_path/'artifacts'))
    def fail(*args):raise ModelHttpError('Sensitive upstream body: do not expose')
    monkeypatch.setattr(semantic_intent,'interpret',fail)
    with TestClient(app) as client:
        gid=client.post('/api/v2/games',json={'prompt':'An automatic forest runner','mode':'live'}).json()['game_id']
        result=client.get('/api/v2/games/'+gid).json()
        assert result['job']['status']=='FAILED' and result['job']['error_code']=='MODEL_HTTP_ERROR'
        assert 'quota' in result['events'][-1]['detail'] and 'Sensitive upstream' not in json.dumps(result)
