from typing import List

from carecall_domain import Call, Chunk


def build_chunks(call: Call) -> List[Chunk]:
    """Build overlapping 2-4 turn dialogue windows for a single call,
    preserving original turn numbers and exact transcript text so retrieval
    can use both lexical and contextual signals while citations stay
    traceable back to the source transcript."""
    turns = call.turns
    chunks: List[Chunk] = []
    for start in range(0, len(turns) - 1):
        window = turns[start:start + 4]
        if len(window) < 2:
            continue
        text = " ".join(f"{turn.speaker}: {turn.text}" for turn in window)
        metadata_parts = [
            call.patient.name,
            call.patient.id,
            call.date,
            call.call_id,
            " ".join(turn.text for turn in window),
        ]
        chunks.append(Chunk(
            chunk_id=f"{call.call_id}:{start + 1}:{start + len(window)}",
            call_id=call.call_id,
            patient_id=call.patient.id,
            patient_name=call.patient.name,
            date=call.date,
            turn_start=start + 1,
            turn_end=start + len(window),
            turns=window,
            metadata_text=" ".join(metadata_parts),
            text=text,
        ))
    return chunks
