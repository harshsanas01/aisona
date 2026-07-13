import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.retrieval import TranscriptRetriever
from app.data_loader import load_transcripts


TRANSLATIONS = load_transcripts(Path(__file__).resolve().parents[2] / 'data' / 'carecall_transcripts.json')
RETRIEVER = TranscriptRetriever(TRANSLATIONS)


def test_retrieval_for_lisinopril():
    results = RETRIEVER.retrieve('lisinopril', limit=5)
    assert any(chunk.call_id == 'call_003' for chunk in results)


def test_retrieval_for_cough():
    results = RETRIEVER.retrieve("Dorothy's cough", limit=10)
    assert any(chunk.call_id in {'call_012', 'call_018'} for chunk in results)


def test_unanswerable_chest_pain_query_has_no_citations():
    results = RETRIEVER.retrieve('chest pain', limit=10)
    assert not results


def test_out_of_domain_weather_query_returns_no_evidence():
    results = RETRIEVER.retrieve("What is today's weather in LA?", limit=10)
    assert not results


def test_out_of_domain_super_bowl_query_returns_no_evidence():
    results = RETRIEVER.retrieve('Who won the Super Bowl?', limit=10)
    assert not results


def test_out_of_domain_bitcoin_query_returns_no_evidence():
    results = RETRIEVER.retrieve('What is the price of Bitcoin?', limit=10)
    assert not results
