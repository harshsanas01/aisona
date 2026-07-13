from abc import ABC, abstractmethod
from typing import List, Optional

from carecall_domain import Call, Patient, Chunk


class CallRepository(ABC):
    """Port for reading and writing calls. Swappable between an in-memory
    JSON-backed implementation (demo mode) and a PostgreSQL implementation
    (production-like mode) without changing any caller."""

    @abstractmethod
    def list_calls(self) -> List[Call]: ...

    @abstractmethod
    def get_call(self, call_id: str) -> Optional[Call]: ...

    @abstractmethod
    def exists(self, call_id: str) -> bool: ...

    @abstractmethod
    def add_call(self, call: Call) -> None: ...


class PatientRepository(ABC):
    @abstractmethod
    def list_patients(self) -> List[Patient]: ...

    @abstractmethod
    def get_patient(self, patient_id: str) -> Optional[Patient]: ...


class ChunkRepository(ABC):
    """Port over the retrieval-unit store. In memory mode, chunks are derived
    on the fly from calls; in PostgreSQL mode they are durable rows with an
    optional pgvector embedding column."""

    @abstractmethod
    def all_chunks(self) -> List[Chunk]: ...

    @abstractmethod
    def chunks_for_call(self, call_id: str) -> List[Chunk]: ...

    @abstractmethod
    def add_chunks(self, chunks: List[Chunk]) -> None: ...
