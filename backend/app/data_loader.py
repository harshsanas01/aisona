import json
from pathlib import Path
from typing import List

from .models import TranscriptCall, TranscriptCorpus


class TranscriptDataError(ValueError):
    pass


def load_transcripts(path: Path | None = None) -> TranscriptCorpus:
    target = path or Path(__file__).resolve().parents[2] / 'data' / 'carecall_transcripts.json'
    if not target.exists():
        raise TranscriptDataError(f'Missing transcript data file: {target}')

    try:
        raw = json.loads(target.read_text())
    except json.JSONDecodeError as exc:
        raise TranscriptDataError(f'Malformed transcript JSON: {exc}') from exc

    if 'calls' not in raw or not isinstance(raw['calls'], list):
        raise TranscriptDataError('Transcript JSON must contain a top-level "calls" array')

    calls: List[TranscriptCall] = []
    seen_ids = set()
    for index, item in enumerate(raw['calls'], start=1):
        try:
            call = TranscriptCall.model_validate(item)
        except Exception as exc:
            raise TranscriptDataError(f'Invalid call entry at index {index}: {exc}') from exc
        if call.call_id in seen_ids:
            raise TranscriptDataError(f'Duplicate call ID found: {call.call_id}')
        seen_ids.add(call.call_id)
        calls.append(call)

    corpus = TranscriptCorpus(calls=calls)
    if len(corpus.calls) != 21:
        raise TranscriptDataError(f'Expected 21 calls but loaded {len(corpus.calls)}')
    return corpus
