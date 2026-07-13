from typing import Dict, List, Optional

from carecall_application.ports.repositories import CallRepository, ChunkRepository, PatientRepository
from carecall_domain import Call, Chunk, DuplicateCallError, Patient


class InMemoryCallRepository(CallRepository):
    def __init__(self, calls: Optional[List[Call]] = None):
        self._calls: Dict[str, Call] = {}
        self._order: List[str] = []
        for call in calls or []:
            self.add_call(call)

    def list_calls(self) -> List[Call]:
        return [self._calls[call_id] for call_id in self._order]

    def get_call(self, call_id: str) -> Optional[Call]:
        return self._calls.get(call_id)

    def exists(self, call_id: str) -> bool:
        return call_id in self._calls

    def add_call(self, call: Call) -> None:
        if call.call_id in self._calls:
            raise DuplicateCallError(f"Call {call.call_id} already exists")
        self._calls[call.call_id] = call
        self._order.append(call.call_id)


class InMemoryPatientRepository(PatientRepository):
    """Patients only exist attached to calls in demo mode - there is no
    standalone patient fixture. Reads live from the CallRepository (rather
    than keeping its own snapshot) so a patient introduced by a newly
    ingested call shows up immediately, matching PostgresPatientRepository's
    behavior of always querying current state."""

    def __init__(self, call_repository: CallRepository):
        self._call_repository = call_repository

    def list_patients(self) -> List[Patient]:
        seen: Dict[str, Patient] = {}
        for call in self._call_repository.list_calls():
            seen.setdefault(call.patient.id, call.patient)
        return list(seen.values())

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        for call in self._call_repository.list_calls():
            if call.patient.id == patient_id:
                return call.patient
        return None


class InMemoryChunkRepository(ChunkRepository):
    def __init__(self, chunks: Optional[List[Chunk]] = None):
        self._chunks: List[Chunk] = []
        self._by_call: Dict[str, List[Chunk]] = {}
        if chunks:
            self.add_chunks(chunks)

    def all_chunks(self) -> List[Chunk]:
        return list(self._chunks)

    def chunks_for_call(self, call_id: str) -> List[Chunk]:
        return list(self._by_call.get(call_id, []))

    def add_chunks(self, chunks: List[Chunk]) -> None:
        for chunk in chunks:
            self._chunks.append(chunk)
            self._by_call.setdefault(chunk.call_id, []).append(chunk)
