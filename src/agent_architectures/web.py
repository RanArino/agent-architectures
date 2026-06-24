"""Local web UI for the three architectures — a driving adapter / composition root.

Parallel to ``cli.py``: instead of printing a console trace, it injects a
``CollectingTrace`` so each run is captured as structured data and served as JSON to a
static page that draws the flow. Live model runs still need ``OPENAI_API_KEY``; the
server and its endpoints boot and report status without one.

Binds to 127.0.0.1 by default — this is a local learning tool, not a public service.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

from .adapters.llm import OpenAIChatLLM
from .adapters.observability import CollectingTrace, InMemoryMetrics
from .adapters.orchestration import HandoffAdapter, OrchestratorAdapter
from .adapters.orchestration.openai_agents_sdk import ArchitectureGraph
from .adapters.tools import build_mock_tools
from .application.orchestrate_workers import OrchestrateWorkers
from .application.ports import AgentMetrics, ArchitectureResult
from .application.single_agent_loop import SingleAgentLoop
from .application.triage_and_handoff import TriageAndHandoff
from .config import Config
from .fixtures import TASKS, resolve_task

load_dotenv()  # read a local .env so the status banner and /api/meta see the key; real env vars still win

STATIC_DIR = Path(__file__).parent / "static"
ARCHITECTURES = ("single-loop", "orchestrator", "handoff")
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def _key_present() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _model() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL)


def _roles(graph: ArchitectureGraph) -> dict[str, object]:
    return {
        "controller": graph.controller.name,
        "specialists": [specialist.name for specialist in graph.specialists],
    }


def _metric_json(metric: AgentMetrics) -> dict[str, object]:
    return {
        "agent": metric.agent,
        "input_tokens": metric.input_tokens,
        "output_tokens": metric.output_tokens,
        "total_tokens": metric.total_tokens,
        "latency_ms": round(metric.latency_ms, 1),
        "cost_usd": metric.cost_usd,
    }


async def _run_architecture(name: str, question: str) -> tuple[ArchitectureResult, CollectingTrace, dict[str, object]]:
    config = Config.from_env()
    tools = build_mock_tools()
    trace = CollectingTrace()
    metrics = InMemoryMetrics()

    if name == "single-loop":
        use_case = SingleAgentLoop(OpenAIChatLLM(config.api_key, config.model), tools, trace, metrics)
        return await use_case.run(question), trace, {"controller": "single-agent", "specialists": []}
    if name == "orchestrator":
        adapter = OrchestratorAdapter(config.model, tools, trace, metrics)
        return await OrchestrateWorkers(adapter).run(question), trace, _roles(adapter.describe())
    adapter = HandoffAdapter(config.model, tools, trace, metrics)
    return await TriageAndHandoff(adapter).run(question), trace, _roles(adapter.describe())


async def meta(request: Request) -> JSONResponse:
    return JSONResponse({
        "tasks": [{"id": task.id, "question": task.question} for task in TASKS],
        "architectures": list(ARCHITECTURES),
        "key_present": _key_present(),
        "model": _model(),
    })


async def run(request: Request) -> JSONResponse:
    body = await request.json()
    name = body.get("architecture")
    if name not in ARCHITECTURES:
        return JSONResponse({"error": f"unknown architecture: {name!r}"}, status_code=400)
    if not _key_present():
        return JSONResponse({"error": "OPENAI_API_KEY is not set; live model runs need it."}, status_code=400)

    task = resolve_task(str(body.get("task", "")))
    try:
        result, trace, roles = await _run_architecture(name, task.question)
    except Exception as exc:  # surface provider/runtime errors to the UI instead of a 500 page
        return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=502)

    return JSONResponse({
        "architecture": name,
        "task": task.id,
        "question": task.question,
        "answer": result.answer,
        "final_agent": result.final_agent,
        "roles": roles,
        "steps": trace.steps(),
        "metrics": [_metric_json(metric) for metric in result.metrics],
    })


async def index(request: Request) -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app = Starlette(routes=[
    Route("/", index),
    Route("/api/meta", meta),
    Route("/api/run", run, methods=["POST"]),
])


def main() -> None:
    import uvicorn

    host = os.getenv("AGENTFLOW_UI_HOST", DEFAULT_HOST)
    port = int(os.getenv("AGENTFLOW_UI_PORT", str(DEFAULT_PORT)))
    print(f"agentflow UI on http://{host}:{port}  (key set: {_key_present()}, model: {_model()})")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
