from types import SimpleNamespace

import pytest

from agent_architectures.adapters.observability import ConsoleTrace, InMemoryMetrics
from agent_architectures.adapters.orchestration import HandoffAdapter
from agent_architectures.adapters.orchestration.openai_agents_sdk import ObservabilityHooks, result_from_sdk
from agent_architectures.adapters.tools import build_mock_tools
from agent_architectures.domain import Message


class RecordingTrace:
    def __init__(self) -> None:
        self.contexts: list[tuple[str, tuple[Message, ...]]] = []

    def context(self, agent: str, messages: list[Message]) -> None:
        self.contexts.append((agent, tuple(messages)))

    def event(self, agent: str, event: str, detail: str) -> None:
        pass


def test_triage_has_no_search_tools_and_handoffs_filter_tool_noise() -> None:
    adapter = HandoffAdapter("gpt-4.1-mini", build_mock_tools(), ConsoleTrace(), InMemoryMetrics())
    graph = adapter.describe()
    assert graph.controller.tool_names == ()
    assert graph.filters_tool_noise
    assert [specialist.tool_names for specialist in graph.specialists] == [
        ("search_web",),
        ("search_wikipedia",),
        ("search_web", "search_wikipedia"),
    ]

    sdk_agent = adapter._build_agent()
    assert not sdk_agent.tools
    assert len(sdk_agent.handoffs) == 3
    assert all(transfer.input_filter is not None for transfer in sdk_agent.handoffs)


def test_final_answer_is_attributed_to_handoff_receiver() -> None:
    sdk_result = SimpleNamespace(final_output="receiver answer", last_agent=SimpleNamespace(name="search_web-specialist"))
    result = result_from_sdk("handoff", sdk_result, ())
    assert result.final_agent == "search_web-specialist"


@pytest.mark.asyncio
async def test_receiver_trace_is_the_filtered_input_given_to_its_model() -> None:
    trace = RecordingTrace()
    hooks = ObservabilityHooks(trace, InMemoryMetrics(), "gpt-4.1-mini")
    receiver = SimpleNamespace(name="search_web-specialist")
    filtered_input = [
        {"role": "user", "content": "According to the web, what is an agent?"},
        {"type": "handoff_output_item", "source_agent": "triage", "target_agent": receiver.name},
    ]

    await hooks.on_llm_start(SimpleNamespace(), receiver, "receiver instructions", filtered_input)

    agent, messages = trace.contexts[0]
    assert agent == receiver.name
    rendered = "\n".join(message.content for message in messages)
    assert "According to the web" in rendered
    assert "triage" in rendered
    assert "function_call_output" not in rendered
