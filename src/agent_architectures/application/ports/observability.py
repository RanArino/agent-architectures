from dataclasses import dataclass
from typing import Protocol, Sequence

from ...domain import Message


@dataclass(frozen=True)
class AgentMetrics:
    agent: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class TracePort(Protocol):
    def context(self, agent: str, messages: Sequence[Message]) -> None: ...
    def event(self, agent: str, event: str, detail: str) -> None: ...


class MetricsPort(Protocol):
    def record(self, metrics: AgentMetrics) -> None: ...
    def all(self) -> tuple[AgentMetrics, ...]: ...
