"""Characterization tests for the pre-refactor CareCall Insight API.

These lock in the exact response shapes of the working demo build so the
upcoming monorepo/layered-architecture refactor can be verified against a
known-good baseline instead of relying on memory of "it worked before".
"""
from fastapi.testclient import TestClient

from carecall_api.main import app

client = TestClient(app)


def test_list_calls_shape():
    response = client.get('/api/calls')
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {'calls'}
    assert len(body['calls']) == 21
    first = body['calls'][0]
    assert set(first.keys()) == {'call_id', 'date', 'patient_name'}


def test_get_call_shape():
    response = client.get('/api/calls/call_003')
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {'call_id', 'date', 'patient', 'duration_seconds', 'turns'}
    assert set(body['patient'].keys()) == {'id', 'name', 'age'}
    assert set(body['turns'][0].keys()) == {'turn_number', 'speaker', 'text'}


def test_ask_response_shape_for_supported_question():
    response = client.post('/api/ask', json={'question': 'What new medication did Margaret Chen start?'})
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        'question', 'answer', 'answerable', 'confidence', 'citations', 'retrieval_debug', 'filters',
    }
    assert body['answerable'] is True
    assert body['citations']
    citation = body['citations'][0]
    assert set(citation.keys()) == {
        'call_id', 'patient_id', 'patient_name', 'date', 'turn_start', 'turn_end', 'quote',
    }
    assert set(body['retrieval_debug'].keys()) == {'mode', 'candidate_count'}


def test_ask_response_shape_for_unanswerable_question():
    response = client.post('/api/ask', json={'question': 'Did anyone mention chest pain?'})
    assert response.status_code == 200
    body = response.json()
    assert body['answerable'] is False
    assert body['confidence'] == 'low'
    assert body['citations'] == []


def test_filters_are_accepted_by_ask_endpoint():
    response = client.post('/api/ask', json={
        'question': 'Which participants have reported feeling dizzy in June?',
        'patient_id': None,
        'start_date': '2026-06-01',
        'end_date': '2026-06-30',
    })
    assert response.status_code == 200
