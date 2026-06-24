from ...application.ports import AgentMetrics


class InMemoryMetrics:
    def __init__(self) -> None:
        self._records: list[AgentMetrics] = []

    def record(self, metrics: AgentMetrics) -> None:
        existing = next((record for record in self._records if record.agent == metrics.agent), None)
        if existing is None:
            self._records.append(metrics)
            return
        cost_usd = None if existing.cost_usd is None or metrics.cost_usd is None else existing.cost_usd + metrics.cost_usd
        combined = AgentMetrics(
            metrics.agent,
            existing.input_tokens + metrics.input_tokens,
            existing.output_tokens + metrics.output_tokens,
            existing.latency_ms + metrics.latency_ms,
            cost_usd,
        )
        self._records[self._records.index(existing)] = combined

    def all(self) -> tuple[AgentMetrics, ...]:
        return tuple(self._records)
