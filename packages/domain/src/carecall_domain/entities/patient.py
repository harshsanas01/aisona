from dataclasses import dataclass


@dataclass(frozen=True)
class Patient:
    id: str
    name: str
    age: int
