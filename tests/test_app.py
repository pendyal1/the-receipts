from fastapi.testclient import TestClient
import app as module
from tests.test_research import FakeSources, FakeModel, SCOPE
from receipts.research import Investigator


def client(monkeypatch):
    monkeypatch.setattr(module,'investigator',Investigator(FakeSources(),FakeModel()))
    monkeypatch.setattr(module,'sessions',module.Sessions())
    return TestClient(module.app)


def test_legacy_chat_and_session_continuation(monkeypatch):
    c=client(monkeypatch)
    first=c.post('/chat',json={'message':'Compare revenue','scope':SCOPE}).json()
    assert {'response','session_id','tool_calls'}<=first.keys()
    assert first['investigation']['status']=='complete'
    follow=c.post('/chat',json={'message':'What was missing?','session_id':first['session_id']}).json()
    assert follow['session_id']==first['session_id']
    assert follow['investigation']['scope']==SCOPE
    assert c.post('/clear',json={'session_id':first['session_id']}).status_code==200
    next_case=c.post('/chat',json={'message':'Compare revenue','scope':SCOPE,'session_id':first['session_id']}).json()
    assert next_case['session_id']!=first['session_id']


def test_separate_browsers_do_not_share_context(monkeypatch):
    c=client(monkeypatch)
    first=c.post('/chat',json={'message':'Compare','scope':SCOPE}).json()
    second=c.post('/chat',json={'message':'Is it good?'}).json()
    assert first['session_id']!=second['session_id']
    assert second['investigation']['status']=='clarification'


def test_input_errors_and_security_headers(monkeypatch):
    c=client(monkeypatch)
    for payload in [{'message':' '},{'message':'x','session_id':'bad'},{'message':'x','scope':dict(SCOPE,through='2030-01-01')}]:
        assert c.post('/chat',json=payload).status_code==422
    response=c.get('/')
    assert response.status_code==200
    assert "script-src 'self'" in response.headers['content-security-policy']
    assert response.headers['x-content-type-options']=='nosniff'
    assert c.get('/static/app.js').status_code==200


def test_source_preview_is_explicitly_not_ai(monkeypatch):
    c=client(monkeypatch)
    data=c.post('/evidence',json={'message':'Compare','scope':SCOPE}).json()
    assert data['investigation']['status']=='preview'
    assert data['investigation']['report'] is None
    assert all(t['agent'] for t in data['tool_calls'])
    assert c.post('/evidence',json={'message':'vague'}).status_code==422


def test_capacity_limit_returns_retryable_status(monkeypatch):
    c=client(monkeypatch)
    monkeypatch.setattr(module,'capacity',__import__('threading').BoundedSemaphore(1))
    module.capacity.acquire()
    assert c.post('/chat',json={'message':'Compare','scope':SCOPE}).status_code==429
    module.capacity.release()
