from dataclasses import replace
from typing import Optional

from carecall_domain import Brief

from ..ports.brief_prose_generator import BriefProseGenerator
from ..ports.repositories import BriefRepository
from .generate_brief import GenerateBriefUseCase


class RegenerateBriefUseCase:
    """Reruns brief generation with an existing brief's own parameters
    (type/date range/patient/include_resolved) and updates it in place, so
    the brief's URL/id stays stable across a regenerate."""

    def __init__(self, brief_repository: BriefRepository, generate_brief: GenerateBriefUseCase):
        self.brief_repository = brief_repository
        self.generate_brief = generate_brief

    def execute(self, brief_id: str, *, prose_generator: Optional[BriefProseGenerator] = None) -> Optional[Brief]:
        existing = self.brief_repository.get(brief_id)
        if existing is None:
            return None

        fresh = self.generate_brief.build(
            brief_type=existing.brief_type,
            start_date=existing.start_date,
            end_date=existing.end_date,
            patient_id=existing.patient_id,
            include_resolved=existing.include_resolved,
        )
        if prose_generator is not None:
            fresh = prose_generator.polish(fresh)
        updated = replace(fresh, brief_id=brief_id, created_at=existing.created_at)
        return self.brief_repository.update(updated)
