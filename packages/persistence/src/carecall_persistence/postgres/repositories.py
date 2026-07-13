import hashlib
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from carecall_application.ports.repositories import CallRepository, ChunkRepository, PatientRepository
from carecall_domain import Call, Chunk, DuplicateCallError, Patient, Turn

from .models import CallRow, PatientRow, TranscriptChunkRow, TranscriptTurnRow


class PostgresPatientRepository(PatientRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def list_patients(self) -> List[Patient]:
        with self._session_factory() as session:
            rows = session.execute(select(PatientRow)).scalars().all()
            return [Patient(id=row.external_patient_id, name=row.name, age=row.age) for row in rows]

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        with self._session_factory() as session:
            row = session.execute(
                select(PatientRow).where(PatientRow.external_patient_id == patient_id)
            ).scalar_one_or_none()
            return Patient(id=row.external_patient_id, name=row.name, age=row.age) if row else None


class PostgresCallRepository(CallRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def list_calls(self) -> List[Call]:
        with self._session_factory() as session:
            rows = session.execute(select(CallRow).order_by(CallRow.call_date)).scalars().all()
            return [self._to_domain(row) for row in rows]

    def get_call(self, call_id: str) -> Optional[Call]:
        with self._session_factory() as session:
            row = session.execute(
                select(CallRow).where(CallRow.external_call_id == call_id)
            ).scalar_one_or_none()
            return self._to_domain(row) if row else None

    def exists(self, call_id: str) -> bool:
        with self._session_factory() as session:
            row_id = session.execute(
                select(CallRow.id).where(CallRow.external_call_id == call_id)
            ).scalar_one_or_none()
            return row_id is not None

    def add_call(self, call: Call) -> None:
        """Idempotent on external_call_id: raises DuplicateCallError instead
        of silently duplicating a re-ingested call. Runs as a single
        transaction - patient upsert, call row, and every turn row commit
        together or not at all."""
        with self._session_factory() as session:
            existing = session.execute(
                select(CallRow.id).where(CallRow.external_call_id == call.call_id)
            ).scalar_one_or_none()
            if existing is not None:
                raise DuplicateCallError(f"Call {call.call_id} already exists")

            patient_row = session.execute(
                select(PatientRow).where(PatientRow.external_patient_id == call.patient.id)
            ).scalar_one_or_none()
            if patient_row is None:
                patient_row = PatientRow(
                    external_patient_id=call.patient.id, name=call.patient.name, age=call.patient.age,
                )
                session.add(patient_row)
                session.flush()

            call_row = CallRow(
                external_call_id=call.call_id,
                patient_id=patient_row.id,
                call_date=call.date,
                duration_seconds=call.duration_seconds,
            )
            session.add(call_row)
            session.flush()

            for index, turn in enumerate(call.turns, start=1):
                session.add(TranscriptTurnRow(
                    call_id=call_row.id, turn_number=index, speaker=turn.speaker, text=turn.text,
                ))
            session.commit()

    @staticmethod
    def _to_domain(row: CallRow) -> Call:
        turns = [Turn(speaker=t.speaker, text=t.text) for t in sorted(row.turns, key=lambda t: t.turn_number)]
        patient = Patient(id=row.patient.external_patient_id, name=row.patient.name, age=row.patient.age)
        return Call(
            call_id=row.external_call_id,
            date=row.call_date,
            patient=patient,
            duration_seconds=row.duration_seconds,
            turns=turns,
        )


class PostgresChunkRepository(ChunkRepository):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def all_chunks(self) -> List[Chunk]:
        with self._session_factory() as session:
            rows = session.execute(select(TranscriptChunkRow)).scalars().all()
            return [self._to_domain(row) for row in rows]

    def chunks_for_call(self, call_id: str) -> List[Chunk]:
        with self._session_factory() as session:
            call_row = session.execute(
                select(CallRow).where(CallRow.external_call_id == call_id)
            ).scalar_one_or_none()
            if call_row is None:
                return []
            rows = session.execute(
                select(TranscriptChunkRow).where(TranscriptChunkRow.call_id == call_row.id)
            ).scalars().all()
            return [self._to_domain(row, call_row=call_row) for row in rows]

    def add_chunks(self, chunks: List[Chunk]) -> None:
        with self._session_factory() as session:
            for chunk in chunks:
                call_row = session.execute(
                    select(CallRow).where(CallRow.external_call_id == chunk.call_id)
                ).scalar_one_or_none()
                if call_row is None:
                    continue
                content_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
                session.add(TranscriptChunkRow(
                    call_id=call_row.id,
                    turn_start=chunk.turn_start,
                    turn_end=chunk.turn_end,
                    text=chunk.text,
                    content_hash=content_hash,
                ))
            session.commit()

    @staticmethod
    def _to_domain(row: TranscriptChunkRow, call_row: Optional[CallRow] = None) -> Chunk:
        call_row = call_row or row.call
        patient = call_row.patient
        turns = [
            Turn(speaker=t.speaker, text=t.text)
            for t in sorted(call_row.turns, key=lambda t: t.turn_number)
            if row.turn_start <= t.turn_number <= row.turn_end
        ]
        metadata_text = " ".join([
            patient.name, patient.external_patient_id, call_row.call_date, call_row.external_call_id,
            " ".join(t.text for t in turns),
        ])
        return Chunk(
            chunk_id=f"{call_row.external_call_id}:{row.turn_start}:{row.turn_end}",
            call_id=call_row.external_call_id,
            patient_id=patient.external_patient_id,
            patient_name=patient.name,
            date=call_row.call_date,
            turn_start=row.turn_start,
            turn_end=row.turn_end,
            turns=turns,
            metadata_text=metadata_text,
            text=row.text,
        )
