from abc import ABC, abstractmethod
from typing import List, Optional

from carecall_domain import Chunk, DateRange


class RetrievalService(ABC):
    """Port for turning a natural-language question into ranked evidence
    chunks. Implementations are free to use lexical search, semantic
    embeddings, a hybrid of both, or a completely different index (e.g.
    OpenSearch) as long as they honor filters and return Chunk objects."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        *,
        limit: int,
        patient_id: Optional[str] = None,
        date_range: Optional[DateRange] = None,
    ) -> List[Chunk]: ...
