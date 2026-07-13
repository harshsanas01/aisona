from fastapi.testclient import TestClient

import pytest

from carecall_api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get('/api/health')
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'ok'
    assert body['calls_loaded'] == 21


def test_get_call_by_id():
    response = client.get('/api/calls/call_003')
    assert response.status_code == 200
    body = response.json()
    assert body['patient']['name'] == 'Margaret Chen'
    assert body['call_id'] == 'call_003'


def test_get_unknown_call_returns_404():
    response = client.get('/api/calls/does_not_exist')
    assert response.status_code == 404


def test_empty_question_is_validated():
    response = client.post('/api/ask', json={'question': '   '})
    assert response.status_code == 422


def test_mock_mode_works_without_openai_key(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    response = client.post('/api/ask', json={'question': 'What new medication did Margaret Chen start?'})
    assert response.status_code == 200
    body = response.json()
    assert body['answerable'] is True
    assert body['citations'][0]['call_id'] == 'call_003'


@pytest.mark.parametrize('question', [
    "What is today's weather in LA?",
    'Who won the Super Bowl?',
    'What is the price of Bitcoin?',
])
def test_out_of_domain_questions_are_rejected(monkeypatch, question):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    response = client.post('/api/ask', json={'question': question})
    assert response.status_code == 200
    body = response.json()
    assert body['answerable'] is False
    assert body['confidence'] == 'low'
    assert body['citations'] == []
