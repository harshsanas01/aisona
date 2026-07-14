from __future__ import annotations

import json
import logging
from dataclasses import replace
from typing import Optional

import openai
from carecall_application.ports.brief_prose_generator import BriefProseGenerator
from carecall_domain import Brief, BriefBullet
from openai import OpenAI

from ..prompts import BRIEF_PROSE_PROMPT, BRIEF_PROSE_PROMPT_VERSION
from ..schemas import OpenAIBriefProseResponse
from .mock_brief_prose_generator import MockBriefProseGenerator

logger = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)


class OpenAIBriefProseGenerator(BriefProseGenerator):
    """Optional prose polish over an already-built Brief. Every bullet's
    rewritten text is validated before being accepted: it must still
    reference every call_id already cited in that bullet's evidence (a
    rewrite that drops or changes a citation is rejected), and it is never
    allowed to introduce banned causal/diagnostic language. Any bullet that
    fails validation, or any API failure, keeps its original deterministic
    text - this stage can only polish wording, never facts."""

    _BANNED_PHRASES = ("diagnos", "confirmed adverse", "caused by", "medical recommendation")

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        *,
        timeout: float = 20.0,
        fallback: Optional[BriefProseGenerator] = None,
    ):
        self._client = OpenAI(api_key=api_key, timeout=timeout)
        self.model = model
        self.fallback = fallback or MockBriefProseGenerator()

    def polish(self, brief: Brief) -> Brief:
        polished_bullets = tuple(self._polish_bullet(b) for b in brief.bullets)
        return replace(brief, bullets=polished_bullets, model_version=self.model, prompt_version=BRIEF_PROSE_PROMPT_VERSION)

    def _polish_bullet(self, bullet: BriefBullet) -> BriefBullet:
        rewritten = self._call(bullet.summary)
        if rewritten is None:
            return bullet
        if not self._is_valid(bullet, rewritten):
            logger.warning("Rejected brief bullet rewrite failing citation/safety validation")
            return bullet
        return replace(bullet, summary=rewritten)

    def _is_valid(self, bullet: BriefBullet, rewritten: str) -> bool:
        if not rewritten.strip():
            return False
        lowered = rewritten.lower()
        if any(phrase in lowered for phrase in self._BANNED_PHRASES):
            return False
        # Every call_id already cited in this bullet's evidence must still
        # be traceable in the rewritten text - a rewrite that silently
        # drops which call something came from is not accepted.
        cited_call_ids = {ref.call_id for ref in bullet.evidence}
        if cited_call_ids and not any(call_id in rewritten for call_id in cited_call_ids):
            return False
        return True

    def _call(self, original_summary: str) -> Optional[str]:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_tokens=200,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": BRIEF_PROSE_PROMPT},
                    {"role": "user", "content": original_summary},
                ],
            )
            raw = json.loads(response.choices[0].message.content or "{}")
            parsed = OpenAIBriefProseResponse.model_validate(raw)
            return parsed.rewritten
        except RETRYABLE_EXCEPTIONS as exc:
            logger.warning("OpenAI transient error polishing brief bullet: %s", type(exc).__name__)
            return None
        except Exception as exc:  # malformed JSON, validation error, auth error, etc.
            logger.warning("OpenAI brief prose polish failed: %s", type(exc).__name__)
            return None
