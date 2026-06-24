from dataclasses import dataclass
from typing import Protocol

from .observability import AgentMetrics


@dataclass(frozen=True)
class ArchitectureResult:
    architecture: str
    answer: str
    final_agent: str
    metrics: tuple[AgentMetrics, ...]


class OrchestratorPort(Protocol):
    async def run(self, question: str) -> ArchitectureResult: ...

