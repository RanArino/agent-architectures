from dataclasses import asdict, dataclass, is_dataclass
import json
from time import perf_counter
from typing import Any

from agents import Agent, AgentHooks, ModelResponse, Runner, function_tool, handoff
from agents.extensions import handoff_filters

from ...application.ports import AgentMetrics, ArchitectureResult, MetricsPort, ToolPort, TracePort
from ...domain import AgentDefinition, Message, TaskDescription
from ...pricing import estimate_cost_usd


@dataclass(frozen=True)
class ArchitectureGraph:
    controller: AgentDefinition
    specialists: tuple[AgentDefinition, ...]
    filters_tool_noise: bool = False


def _sdk_tool(tool: ToolPort, trace: TracePort, owner: str):
    async def search(query: str) -> str:
        """Search the specialist's assigned mocked source."""
        result = await tool.execute(query)
        trace.event(owner, "tool result", f"{tool.name} -> {result}")
        return result

    return function_tool(search, name_override=tool.name, description_override=tool.description)


def _summary_extractor(trace: TracePort, worker: str):
    async def extract(result: object) -> str:
        summary = str(result.final_output)  # type: ignore[attr-defined]
        trace.event("orchestrator", "worker summary", f"{worker} -> {summary}")
        return summary

    return extract


def _input_message(item: object) -> Message:
    if isinstance(item, dict):
        data = item
    elif hasattr(item, "model_dump"):
        data = item.model_dump(exclude_none=True)  # type: ignore[union-attr]
    elif is_dataclass(item):
        data = asdict(item)  # type: ignore[arg-type]
    else:
        data = {"type": type(item).__name__, "value": repr(item)}
    role = str(data.get("role") or data.get("type") or "item")
    name = data.get("name")
    return Message(role, json.dumps(data, ensure_ascii=False, sort_keys=True, default=str), name=str(name) if name else None)


class ObservabilityHooks(AgentHooks):
    def __init__(self, trace: TracePort, metrics: MetricsPort, model: str) -> None:
        self._trace = trace
        self._metrics = metrics
        self._model = model
        self._llm_started = 0.0

    async def on_llm_start(
        self,
        context: object,
        agent: Agent,
        system_prompt: str | None,
        input_items: list[Any],
    ) -> None:
        self._llm_started = perf_counter()
        messages = [_input_message(item) for item in input_items]
        if system_prompt:
            messages.insert(0, Message("system", system_prompt))
        self._trace.context(agent.name, messages)

    async def on_llm_end(self, context: object, agent: Agent, response: ModelResponse) -> None:
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        self._metrics.record(AgentMetrics(
            agent.name,
            input_tokens,
            output_tokens,
            (perf_counter() - self._llm_started) * 1000,
            estimate_cost_usd(self._model, input_tokens, output_tokens),
        ))


def _handoff_callback(trace: TracePort, receiver: str):
    def record_handoff(context: object) -> None:
        trace.event("triage", "handoff", f"control -> {receiver}")

    return record_handoff


def result_from_sdk(architecture: str, result: object, metrics: tuple[AgentMetrics, ...]) -> ArchitectureResult:
    return ArchitectureResult(
        architecture,
        str(result.final_output),  # type: ignore[attr-defined]
        result.last_agent.name,  # type: ignore[attr-defined]
        metrics,
    )


class OrchestratorAdapter:
    def __init__(self, model: str, tools: tuple[ToolPort, ...], trace: TracePort, metrics: MetricsPort) -> None:
        self._model = model
        self._tools = tools
        self._trace = trace
        self._metrics = metrics

    def describe(self) -> ArchitectureGraph:
        workers = tuple(AgentDefinition(f"{tool.name}-specialist", "Research one source", (tool.name,)) for tool in self._tools)
        controller = AgentDefinition("orchestrator", "Delegate research and integrate summaries", tuple(f"research_{tool.name.removeprefix('search_')}" for tool in self._tools))
        return ArchitectureGraph(controller, workers)

    def _build_agent(self) -> Agent:
        workers = [
            Agent(
                name=f"{tool.name}-specialist",
                instructions="Use your one search tool. Return a concise factual summary, not raw process notes.",
                tools=[_sdk_tool(tool, self._trace, f"{tool.name}-specialist")],
                model=self._model,
                hooks=ObservabilityHooks(self._trace, self._metrics, self._model),
            )
            for tool in self._tools
        ]
        worker_tools = [
            worker.as_tool(
                tool_name=f"research_{tool.name.removeprefix('search_')}",
                tool_description=f"Delegate isolated research to {worker.name}.",
                parameters=TaskDescription,
                include_input_schema=True,
                custom_output_extractor=_summary_extractor(self._trace, worker.name),
            )
            for worker, tool in zip(workers, self._tools, strict=True)
        ]
        return Agent(
            name="orchestrator",
            instructions=(
                "Answer directly when no research is needed. Otherwise delegate to the relevant worker tools; "
                "call both in the same turn when comparing sources. Integrate only their returned summaries."
            ),
            tools=worker_tools,
            model=self._model,
            hooks=ObservabilityHooks(self._trace, self._metrics, self._model),
        )

    async def run(self, question: str) -> ArchitectureResult:
        result = await Runner.run(self._build_agent(), question)
        return result_from_sdk("orchestrator", result, self._metrics.all())


class HandoffAdapter:
    def __init__(self, model: str, tools: tuple[ToolPort, ...], trace: TracePort, metrics: MetricsPort) -> None:
        self._model = model
        self._tools = tools
        self._trace = trace
        self._metrics = metrics

    def describe(self) -> ArchitectureGraph:
        specialists = tuple(AgentDefinition(f"{tool.name}-specialist", "Own the dialogue after transfer", (tool.name,)) for tool in self._tools)
        specialists += (AgentDefinition("comparison-specialist", "Compare both sources after transfer", tuple(tool.name for tool in self._tools)),)
        return ArchitectureGraph(AgentDefinition("triage", "Transfer control", ()), specialists, filters_tool_noise=True)

    def _build_agent(self) -> Agent:
        specialists = [
            Agent(
                name=f"{tool.name}-specialist",
                handoff_description=f"Use for questions needing {tool.name}.",
                instructions="You now own the dialogue. Use your search tool and give the final answer.",
                tools=[_sdk_tool(tool, self._trace, f"{tool.name}-specialist")],
                model=self._model,
                hooks=ObservabilityHooks(self._trace, self._metrics, self._model),
            )
            for tool in self._tools
        ]
        specialists.append(Agent(
            name="comparison-specialist",
            handoff_description="Use for questions that compare web and Wikipedia.",
            instructions="You now own the dialogue. Search both sources and give the final comparison.",
            tools=[_sdk_tool(tool, self._trace, "comparison-specialist") for tool in self._tools],
            model=self._model,
            hooks=ObservabilityHooks(self._trace, self._metrics, self._model),
        ))
        transfers = [
            handoff(
                specialist,
                input_filter=handoff_filters.remove_all_tools,
                on_handoff=_handoff_callback(self._trace, specialist.name),
            )
            for specialist in specialists
        ]
        return Agent(
            name="triage",
            instructions="Answer plain questions yourself. Transfer research questions to the single best specialist.",
            handoffs=transfers,
            model=self._model,
            hooks=ObservabilityHooks(self._trace, self._metrics, self._model),
        )

    async def run(self, question: str) -> ArchitectureResult:
        result = await Runner.run(self._build_agent(), question)
        return result_from_sdk("handoff", result, self._metrics.all())
