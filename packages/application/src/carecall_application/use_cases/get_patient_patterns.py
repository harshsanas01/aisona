from typing import List, Optional

from carecall_domain import PatientPattern

from ..ports.repositories import PatternRepository


class GetPatientPatternsUseCase:
    def __init__(self, pattern_repository: PatternRepository):
        self.pattern_repository = pattern_repository

    def execute(
        self, patient_id: str, *, status: Optional[str] = None, severity: Optional[str] = None,
    ) -> List[PatientPattern]:
        patterns = self.pattern_repository.list_for_patient(patient_id)
        if status:
            patterns = [p for p in patterns if p.status == status]
        if severity:
            patterns = [p for p in patterns if p.severity == severity]
        return sorted(patterns, key=lambda p: p.latest_observed_date, reverse=True)
