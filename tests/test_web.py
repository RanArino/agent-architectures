import pytest
from starlette.testclient import TestClient

from agent_architectures.adapters.observability import CollectingTrace
from agent_architectures.domain import Message
from agent_architectures.web import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return TestClient(app)


def test_collecting_trace_records_context_growth_and_events() -> None:
    trace = CollectingTrace()
    trace.context("single-agent", [Message("user", "hello")])
    trace.event("single-agent", "tool", "search_web -> result")
    trace.context("single-agent", [Message("user", "hello"), Message("tool", "result")])

    steps = trace.steps()
    assert [step["kind"] for step in steps] == ["context", "event", "context"]
    assert steps[0]["count"] == 1 and steps[2]["count"] == 2
    assert steps[1]["event"] == "tool"
    assert all(step["seq"] == i for i, step in enumerate(steps))


def test_index_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Agent Flow Visualizer" in response.text


def test_meta_lists_tasks_and_reports_missing_key(client: TestClient) -> None:
    body = client.get("/api/meta").json()
    assert [task["id"] for task in body["tasks"]] == ["plain", "single-source", "compare"]
    assert body["architectures"] == ["single-loop", "orchestrator", "handoff"]
    assert body["key_present"] is False


def test_run_rejects_unknown_architecture(client: TestClient) -> None:
    response = client.post("/api/run", json={"architecture": "swarm", "task": "plain"})
    assert response.status_code == 400
    assert "unknown architecture" in response.json()["error"]


def test_run_requires_a_key_for_live_models(client: TestClient) -> None:
    response = client.post("/api/run", json={"architecture": "single-loop", "task": "plain"})
    assert response.status_code == 400
    assert "OPENAI_API_KEY" in response.json()["error"]
