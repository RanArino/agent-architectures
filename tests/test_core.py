import io

import pytest

from agent_architectures.adapters.observability import ConsoleTrace, InMemoryMetrics
from agent_architectures.adapters.tools import build_mock_tools
from agent_architectures.application.ports import AgentMetrics
from agent_architectures.config import Config
from agent_architectures.domain import Message
from agent_architectures.fixtures import TASKS, resolve_task
from agent_architectures.pricing import estimate_cost_usd


@pytest.mark.asyncio
async def test_mock_tools_are_canned_and_key_free() -> None:
    web, wikipedia = build_mock_tools()
    assert "Agent loops" in await web.execute("agents")
    assert "intelligent agent" in await wikipedia.execute("agents")


def test_trace_and_metrics_implement_learning_instruments() -> None:
    stream = io.StringIO()
    trace = ConsoleTrace(stream)
    trace.context("researcher", (Message("user", "question"),))
    trace.event("researcher", "tool", "canned result")
    assert "[researcher] context" in stream.getvalue()
    assert "tool: canned result" in stream.getvalue()

    metrics = InMemoryMetrics()
    metrics.record(AgentMetrics("researcher", 10, 2, 1.5))
    metrics.record(AgentMetrics("researcher", 5, 1, 2.5))
    assert metrics.all()[0].total_tokens == 18
    assert metrics.all()[0].latency_ms == 4.0


def test_fixtures_and_free_text_resolution() -> None:
    assert [task.id for task in TASKS] == ["plain", "single-source", "compare"]
    assert resolve_task("plain") == TASKS[0]
    assert resolve_task("my question").question == "my question"


def test_config_fails_fast_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # Stub load_dotenv so a developer's local .env can't repopulate the key and
    # mask the failure — this stays a deterministic, key-free check.
    monkeypatch.setattr("agent_architectures.config.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        Config.from_env()


def test_default_model_cost_estimate() -> None:
    assert estimate_cost_usd("gpt-4.1-mini", 1_000_000, 1_000_000) == pytest.approx(2.0)
    assert estimate_cost_usd("unknown", 10, 10) is None
