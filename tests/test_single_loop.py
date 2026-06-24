from collections.abc import Sequence

import pytest

from agent_architectures.adapters.observability import InMemoryMetrics
from agent_architectures.adapters.tools import build_mock_tools
from agent_architectures.application.ports import LLMResponse, ToolCall, ToolPort
from agent_architectures.application.single_agent_loop import SingleAgentLoop
from agent_architectures.domain import Message


class RecordingTrace:
    def __init__(self) -> None:
        self.context_sizes: list[int] = []

    def context(self, agent: str, messages: Sequence[Message]) -> None:
        self.context_sizes.append(len(messages))

    def event(self, agent: str, event: str, detail: str) -> None:
        pass


class ScriptedLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, messages: Sequence[Message], tools: Sequence[ToolPort]) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(tool_calls=(ToolCall("call-1", "search_wikipedia", {"query": "agent"}),), input_tokens=10, output_tokens=3)
        assert messages[-1].role == "tool"
        return LLMResponse("An agent perceives and acts toward goals.", input_tokens=20, output_tokens=8)


@pytest.mark.asyncio
async def test_single_loop_feeds_tool_result_back_into_growing_context() -> None:
    trace = RecordingTrace()
    result = await SingleAgentLoop(ScriptedLLM(), build_mock_tools(), trace, InMemoryMetrics()).run("Define an agent")
    assert trace.context_sizes == [2, 4]
    assert result.final_agent == "single-agent"
    assert result.metrics[0].total_tokens == 41

