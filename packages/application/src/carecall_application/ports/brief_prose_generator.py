from abc import ABC, abstractmethod

from carecall_domain import Brief


class BriefProseGenerator(ABC):
    """Optional LLM stage that may only rephrase a brief's bullet prose
    after deterministic selection - it can never add a bullet, change which
    patient/evidence a bullet is about, or invent a new claim. The
    deterministic (mock) implementation is a no-op passthrough and is what
    CI and demo mode always use; an LLM-backed implementation must validate
    its own output before accepting it (see docs/architecture/audit-trail.md
    sibling ADR on citation validation) and fall back to the original
    deterministic prose on any failure."""

    @abstractmethod
    def polish(self, brief: Brief) -> Brief: ...
