from types import SimpleNamespace

import pytest
from agents import ModelResponse
from agents.usage import Usage

from agent_architectures.adapters.observability import ConsoleTrace, InMemoryMetrics
from agent_architectures.adapters.orchestration import OrchestratorAdapter
from agent_architectures.adapters.orchestration.openai_agents_sdk import ObservabilityHooks
from agent_architectures.adapters.tools import build_mock_tools
from agent_architectures.domain import Message


class RecordingTrace:
    def __init__(self) -> None:
        self.contexts: list[tuple[str, tuple[Message, ...]]] = []

    def context(self, agent: str, messages: list[Message]) -> None:
        self.contexts.append((agent, tuple(messages)))

    def event(self, agent: str, event: str, detail: str) -> None:
        pass


def test_manager_owns_only_worker_tools_and_workers_are_least_privilege() -> None:
    adapter = OrchestratorAdapter("gpt-4.1-mini", build_mock_tools(), ConsoleTrace(), InMemoryMetrics())
    graph = adapter.describe()
    assert graph.controller.tool_names == ("research_web", "research_wikipedia")
    assert all(not name.startswith("search_") for name in graph.controller.tool_names)
    assert [worker.tool_names for worker in graph.specialists] == [("search_web",), ("search_wikipedia",)]

    sdk_agent = adapter._build_agent()
    assert len(sdk_agent.tools) == 2
    assert all("objective" in tool.params_json_schema["properties"] for tool in sdk_agent.tools)
    assert not sdk_agent.handoffs


@pytest.mark.asyncio
async def test_sdk_hooks_use_response_local_usage_and_real_model_input() -> None:
    trace = RecordingTrace()
    metrics = InMemoryMetrics()
    hooks = ObservabilityHooks(trace, metrics, "gpt-4.1-mini")
    agent = SimpleNamespace(name="orchestrator")
    model_input = [
        {"role": "user", "content": "Compare sources"},
        {"type": "function_call", "name": "research_web", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "worker-1", "output": "worker summary"},
    ]

    await hooks.on_llm_start(SimpleNamespace(), agent, "manager instructions", model_input)
    cumulative_context = SimpleNamespace(usage=Usage(input_tokens=10_000, output_tokens=5_000))
    response = ModelResponse([], Usage(input_tokens=40, output_tokens=8), None)
    await hooks.on_llm_end(cumulative_context, agent, response)

    assert metrics.all()[0].input_tokens == 40
    assert metrics.all()[0].output_tokens == 8
    rendered_context = "\n".join(message.content for message in trace.contexts[0][1])
    assert "manager instructions" in rendered_context
    assert "research_web" in rendered_context
    assert "worker summary" in rendered_context
