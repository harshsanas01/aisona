from typing import List

from carecall_domain import Patient

from ..ports.repositories import PatientRepository


class ListPatientsUseCase:
    def __init__(self, patient_repository: PatientRepository):
        self.patient_repository = patient_repository

    def execute(self) -> List[Patient]:
        return self.patient_repository.list_patients()
