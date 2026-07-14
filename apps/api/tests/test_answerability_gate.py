from carecall_llm.grounding import HeuristicAnswerabilityGate

GATE = HeuristicAnswerabilityGate()


def test_chest_pain_question_is_unanswerable_regardless_of_evidence():
    assert GATE.is_unanswerable('Did anyone mention chest pain?', chunks=[object()]) is True


def test_fall_negation_question_is_unanswerable():
    assert GATE.is_unanswerable('Has any participant fallen recently?', chunks=[object()]) is True


def test_ordinary_symptom_question_is_not_gated():
    assert GATE.is_unanswerable('Who has been having trouble sleeping?', chunks=[object()]) is False
