from fastapi.testclient import TestClient

from carecall_api.main import app

client = TestClient(app)


def test_list_patients_returns_all_21_unique_patients():
    response = client.get('/api/patients')
    assert response.status_code == 200
    body = response.json()
    ids = [p['id'] for p in body['patients']]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 1
    assert 'P-1001' in ids  # Margaret Chen


def test_ask_response_reports_applied_filters():
    response = client.post('/api/ask', json={
        'question': 'Which participants have reported feeling dizzy in June?',
        'start_date': '2026-06-01',
        'end_date': '2026-06-30',
    })
    assert response.status_code == 200
    body = response.json()
    assert body['filters'] == {'patient_id': None, 'start_date': '2026-06-01', 'end_date': '2026-06-30'}


def test_invalid_date_range_returns_422():
    response = client.post('/api/ask', json={
        'question': 'Who has been having trouble sleeping?',
        'start_date': '2026-06-30',
        'end_date': '2026-06-01',
    })
    assert response.status_code == 422


def test_safety_events_includes_dizziness_for_known_call():
    response = client.get('/api/safety-events', params={'call_id': 'call_009'})
    assert response.status_code == 200
    body = response.json()
    categories = {e['category'] for e in body['safety_events']}
    assert 'dizziness' in categories
    for event in body['safety_events']:
        assert event['call_id'] == 'call_009'
        assert event['classifier_type'] == 'deterministic'


def test_safety_events_can_filter_by_category():
    response = client.get('/api/safety-events', params={'category': 'fall_or_near_fall'})
    assert response.status_code == 200
    body = response.json()
    assert body['safety_events']
    assert all(e['category'] == 'fall_or_near_fall' for e in body['safety_events'])


def test_safety_events_do_not_flag_assistant_turns():
    response = client.get('/api/safety-events')
    assert response.status_code == 200
    body = response.json()
    # call_007's assistant turn asks "Any dizziness, swelling, or coughing
    # since starting...?" - an assistant question must never itself count
    # as a participant safety report.
    assert not any(e['call_id'] == 'call_007' for e in body['safety_events'])
