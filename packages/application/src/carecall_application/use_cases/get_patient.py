from typing import Optional

from carecall_domain import Patient

from ..ports.repositories import PatientRepository


class GetPatientUseCase:
    def __init__(self, patient_repository: PatientRepository):
        self.patient_repository = patient_repository

    def execute(self, patient_id: str) -> Optional[Patient]:
        return self.patient_repository.get_patient(patient_id)
