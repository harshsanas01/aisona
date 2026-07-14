from __future__ import annotations

import json
import logging
import time
from typing import List, Optional

import openai
from carecall_domain import (
    TIMELINE_EVENT_TYPES,
    Call,
    DeterministicTimelineExtractor,
    TimelineEvent,
    TimelineExtractor,
    build_timeline_event,
)
from openai import OpenAI

from ..prompts import TIMELINE_EXTRACTION_PROMPT
from ..schemas import OpenAITimelineExtractionResponse

logger = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)


class OpenAITimelineExtractor(TimelineExtractor):
    """Optional, swappable enhancement over DeterministicTimelineExtractor.
    The model only ever proposes (turn_number, event_type, confidence) -
    every citation field (call_id, turn range, quote) is reconstructed by
    this class directly from the real Call object via
    build_timeline_event(), never trusted from the model's own output. Any
    candidate with a turn_number outside the transcript or an event_type
    outside TIMELINE_EVENT_TYPES is dropped rather than guessed at. Falls
    back to the deterministic extractor on any timeout, rate limit, or
    malformed response, so a flaky provider can never leave a call
    unprocessed."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        *,
        timeout: float = 20.0,
        max_retries: int = 2,
        max_tokens: int = 800,
        fallback: Optional[TimelineExtractor] = None,
    ):
        self._client = OpenAI(api_key=api_key, timeout=timeout)
        self.model = model
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self.fallback = fallback or DeterministicTimelineExtractor()

    def extract(self, call: Call) -> List[TimelineEvent]:
        transcript_text = "\n".join(
            f"{i}. [{turn.speaker}] {turn.text}" for i, turn in enumerate(call.turns, start=1)
        )
        payload = self._call_with_retry(transcript_text)
        if payload is None:
            return self.fallback.extract(call)

        events: List[TimelineEvent] = []
        seen_dedupe_keys = set()
        for candidate in payload.events:
            if candidate.event_type not in TIMELINE_EVENT_TYPES:
                continue
            if not (1 <= candidate.turn_number <= len(call.turns)):
                continue
            quote = call.turns[candidate.turn_number - 1].text
            event = build_timeline_event(
                call,
                candidate.turn_number,
                candidate.event_type,
                quote,
                confidence=candidate.confidence if candidate.confidence in ("high", "medium", "low") else "low",
                extraction_method="llm",
            )
            if event.dedupe_key in seen_dedupe_keys:
                continue
            seen_dedupe_keys.add(event.dedupe_key)
            events.append(event)
        return events

    def _call_with_retry(self, transcript_text: str) -> Optional[OpenAITimelineExtractionResponse]:
        delay = 0.5
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    temperature=0,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": TIMELINE_EXTRACTION_PROMPT},
                        {"role": "user", "content": f"Numbered transcript:\n{transcript_text}"},
                    ],
                )
                raw = json.loads(response.choices[0].message.content or "{}")
                return OpenAITimelineExtractionResponse.model_validate(raw)
            except RETRYABLE_EXCEPTIONS as exc:
                logger.warning("OpenAI transient error on attempt %s: %s", attempt + 1, type(exc).__name__)
                if attempt == self.max_retries:
                    return None
                time.sleep(delay)
                delay *= 2
            except Exception as exc:  # malformed JSON, validation error, auth error, etc.
                logger.warning("OpenAI timeline extraction failed: %s", type(exc).__name__)
                return None
        return None


__all__ = ["OpenAITimelineExtractor"]
