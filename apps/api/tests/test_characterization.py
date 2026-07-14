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
    # request_id correlates this answer with its audit-trail record (see
    # GET /api/v1/audit/questions/{request_id}) - added deliberately for
    # the "Why this answer?" developer drawer, never a way to recover the
    # raw question text.
    assert set(body.keys()) == {
        'question', 'answer', 'answerable', 'confidence', 'citations', 'retrieval_debug', 'filters', 'request_id',
    }
    assert body['request_id']
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


def test_health_response_shape():
    """Locks the exact health payload shape - the web app header status
    badges read storage_mode/answer_mode directly off this response, and
    developer_mode gates whether developer-only UI (Why this answer?,
    Retrieval Lab) is shown at all."""
    response = client.get('/api/health')
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        'status', 'calls_loaded', 'retrieval_mode', 'storage_mode', 'answer_mode', 'developer_mode',
    }


def test_safety_events_response_shape():
    response = client.get('/api/safety-events', params={'call_id': 'call_009'})
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {'safety_events'}
    event = body['safety_events'][0]
    assert set(event.keys()) == {
        'category', 'severity', 'call_id', 'turn_number', 'matched_text', 'explanation', 'classifier_type',
    }


def test_gus_fall_is_not_attributed_to_samuel_at_the_classifier_level():
    """Domain-level guard for the third-party-attribution bug class: call_021
    is Samuel Rivera's call, but the fall/sprain is reported as happening to
    his neighbor Gus, not to Samuel himself. The deterministic safety
    classifier must still flag the turn (it is operationally relevant) but
    matched_text is always the verbatim turn text, never a claim about who
    it happened to - that judgment is left to the human reviewer. See also
    adv9 ("Did Samuel fall?") in data/evaluation/adversarial_questions.json
    for the same guarantee enforced at the grounded-answer layer."""
    call_response = client.get('/api/calls/call_021')
    assert call_response.status_code == 200
    assert call_response.json()['patient']['name'] == 'Samuel Rivera'

    events_response = client.get('/api/safety-events', params={'call_id': 'call_021'})
    assert events_response.status_code == 200
    fall_events = [e for e in events_response.json()['safety_events'] if e['category'] == 'fall_or_near_fall']
    assert fall_events, 'expected the fall_or_near_fall category to be flagged for call_021'
    for event in fall_events:
        assert 'Gus' in event['matched_text']
        assert 'Samuel' not in event['matched_text']
