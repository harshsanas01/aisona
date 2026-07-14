from pathlib import Path

from carecall_persistence.in_memory import load_calls_from_json
from carecall_retrieval import HybridRetriever, build_chunks

REPO_ROOT = Path(__file__).resolve().parents[3]
CALLS = load_calls_from_json(REPO_ROOT / 'data' / 'raw' / 'carecall_transcripts.json')
CHUNKS = [chunk for call in CALLS for chunk in build_chunks(call)]
RETRIEVER = HybridRetriever(CHUNKS)


def test_retrieval_for_lisinopril():
    results = RETRIEVER.retrieve('lisinopril', limit=5)
    assert any(chunk.call_id == 'call_003' for chunk in results)


def test_retrieval_for_cough():
    results = RETRIEVER.retrieve("Dorothy's cough", limit=10)
    assert any(chunk.call_id in {'call_012', 'call_018'} for chunk in results)


def test_out_of_domain_weather_query_returns_no_evidence():
    results = RETRIEVER.retrieve("What is today's weather in LA?", limit=10)
    assert not results


def test_out_of_domain_super_bowl_query_returns_no_evidence():
    results = RETRIEVER.retrieve('Who won the Super Bowl?', limit=10)
    assert not results


def test_out_of_domain_bitcoin_query_returns_no_evidence():
    results = RETRIEVER.retrieve('What is the price of Bitcoin?', limit=10)
    assert not results
