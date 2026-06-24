from dataclasses import dataclass


@dataclass(frozen=True)
class WorkerSummary:
    worker: str
    content: str

