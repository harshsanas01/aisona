import json
from pathlib import Path

from carecall_api.lifespan import build_container

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / 'data' / 'evaluation' / 'carecall_questions.json'

container = build_container()
questions = json.loads(QUESTIONS_PATH.read_text())['questions']

score = 0
for question in questions:
    response = container.ask_question.execute(question['question'])
    cited_calls = sorted({citation.call_id for citation in response.citations})
    expected = sorted(question['expected_source_calls'])
    if not expected:
        hit = not response.citations and not response.answerable
    else:
        hit = all(call_id in cited_calls for call_id in expected)
    score += int(hit)
    status = 'PASS' if hit else 'FAIL'
    print(f"{question['id']} {status} expected={expected} cited={cited_calls}")

print(f"Retrieval grounding accuracy: {score}/{len(questions)}")
