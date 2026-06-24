import json
from time import perf_counter

from ..domain import ContextWindow
from .ports import AgentMetrics, ArchitectureResult, LLMPort, MetricsPort, ToolPort, TracePort


MAX_TURNS = 8


class SingleAgentLoop:
    def __init__(self, llm: LLMPort, tools: tuple[ToolPort, ...], trace: TracePort, metrics: MetricsPort) -> None:
        self._llm = llm
        self._tools = {tool.name: tool for tool in tools}
        self._trace = trace
        self._metrics = metrics

    async def run(self, question: str) -> ArchitectureResult:
        context = ContextWindow("single-agent")
        context.add("system", "Answer the user. Use the available search tools only when needed.")
        context.add("user", question)
        started = perf_counter()
        input_tokens = output_tokens = 0
        cost_usd: float | None = 0.0

        for _ in range(MAX_TURNS):
            self._trace.context(context.owner, context.messages)
            response = await self._llm.complete(context.messages, tuple(self._tools.values()))
            input_tokens += response.input_tokens
            output_tokens += response.output_tokens
            cost_usd = None if cost_usd is None or response.cost_usd is None else cost_usd + response.cost_usd
            if not response.tool_calls:
                context.add("assistant", response.content)
                return self._finish(response.content, started, input_tokens, output_tokens, cost_usd)
            context.add("assistant", json.dumps([call.__dict__ for call in response.tool_calls]))
            for call in response.tool_calls:
                tool = self._tools.get(call.name)
                if tool is None:
                    raise RuntimeError(f"model requested unknown tool: {call.name}")
                result = await tool.execute(call.arguments.get("query", question))
                self._trace.event(context.owner, "tool", f"{call.name} -> {result}")
                context.add("tool", result, name=call.name, tool_call_id=call.id)
        raise RuntimeError(f"agent exceeded {MAX_TURNS} turns")

    def _finish(self, answer: str, started: float, input_tokens: int, output_tokens: int, cost_usd: float | None) -> ArchitectureResult:
        record = AgentMetrics("single-agent", input_tokens, output_tokens, (perf_counter() - started) * 1000, cost_usd)
        self._metrics.record(record)
        return ArchitectureResult("single-loop", answer, "single-agent", self._metrics.all())
