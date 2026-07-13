import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from app.answer_service import AnswerService
from app.data_loader import load_transcripts

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS_PATH = ROOT / 'data' / 'carecall_transcripts.json'
QUESTIONS_PATH = ROOT / 'data' / 'carecall_questions.json'

corpus = load_transcripts(TRANSCRIPTS_PATH)
service = AnswerService(corpus)
questions = json.loads(QUESTIONS_PATH.read_text())['questions']

score = 0
for question in questions:
    response = service.answer(question['question'])
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
