from __future__ import annotations

import json
import logging
import time
from typing import List, Optional

import openai
from openai import OpenAI

from carecall_application.dto.answer import GroundedAnswer
from carecall_application.ports.answer_generator import AnswerGenerator
from carecall_domain import Chunk

from ..prompts import PROMPT_VERSION, SYSTEM_PROMPT
from ..schemas import OpenAIStructuredAnswer
from .mock_provider import MockAnswerGenerator

logger = logging.getLogger(__name__)

# Errors worth a short exponential backoff retry - anything else (auth
# failure, bad request, validation error) is not transient and should fall
# back immediately instead of retrying a request that will never succeed.
RETRYABLE_EXCEPTIONS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)


class OpenAIAnswerGenerator(AnswerGenerator):
    """OpenAI-backed answer generator. Falls back to a deterministic mock
    generator on any timeout, rate limit, malformed response, or
    unanswerable model output, so a flaky provider can never crash a
    request or silently return an empty answer."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        *,
        timeout: float = 20.0,
        max_retries: int = 2,
        max_tokens: int = 500,
        fallback: Optional[AnswerGenerator] = None,
    ):
        self._client = OpenAI(api_key=api_key, timeout=timeout)
        self.model = model
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self.fallback = fallback or MockAnswerGenerator()

    def generate(self, question: str, evidence: List[Chunk], filters: dict) -> GroundedAnswer:
        if not evidence:
            return self.fallback.generate(question, evidence, filters)

        evidence_text = "\n".join(
            f"[{chunk.chunk_id}] {chunk.patient_name} {chunk.date}: {chunk.text}"
            for chunk in evidence[:3]
        )
        payload = self._call_with_retry(question, evidence_text)
        if payload is None or not payload.answerable or not payload.answer.strip():
            return self.fallback.generate(question, evidence, filters)

        # Never trust evidence ids the model didn't actually receive - a
        # hallucinated id is dropped, and if none are valid we fall back to
        # the top evidence rather than emitting a citation-less answer.
        evidence_ids = {chunk.chunk_id for chunk in evidence}
        valid_ids = [eid for eid in payload.used_evidence_ids if eid in evidence_ids]
        if not valid_ids:
            valid_ids = [chunk.chunk_id for chunk in evidence[:3]]

        return GroundedAnswer(
            answerable=True,
            answer=payload.answer,
            used_evidence_ids=valid_ids,
            confidence=payload.confidence or "medium",
            model_name=self.model,
            prompt_version=PROMPT_VERSION,
        )

    def _call_with_retry(self, question: str, evidence_text: str) -> Optional[OpenAIStructuredAnswer]:
        delay = 0.5
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    temperature=0,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Question: {question}\nEvidence:\n{evidence_text}"},
                    ],
                )
                raw = json.loads(response.choices[0].message.content or "{}")
                return OpenAIStructuredAnswer.model_validate(raw)
            except RETRYABLE_EXCEPTIONS as exc:
                logger.warning("OpenAI transient error on attempt %s: %s", attempt + 1, type(exc).__name__)
                if attempt == self.max_retries:
                    return None
                time.sleep(delay)
                delay *= 2
            except Exception as exc:  # malformed JSON, validation error, auth error, etc.
                logger.warning("OpenAI answer generation failed: %s", type(exc).__name__)
                return None
        return None
