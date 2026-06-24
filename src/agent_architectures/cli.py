import argparse
import asyncio
from collections.abc import Awaitable, Callable

from .adapters.llm import OpenAIChatLLM
from .adapters.observability import ConsoleTrace, InMemoryMetrics
from .adapters.orchestration import HandoffAdapter, OrchestratorAdapter
from .adapters.tools import build_mock_tools
from .application.orchestrate_workers import OrchestrateWorkers
from .application.single_agent_loop import SingleAgentLoop
from .application.triage_and_handoff import TriageAndHandoff
from .application.ports import ArchitectureResult
from .config import Config
from .fixtures import TASKS, resolve_task


RunArchitecture = Callable[[str], Awaitable[ArchitectureResult]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentflow", description="Watch three agent architectures run.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("tasks", help="List shared task presets")
    for name in ("single-loop", "orchestrator", "handoff"):
        command = commands.add_parser(name, help=f"Run the {name} architecture")
        command.add_argument("task", help="plain, single-source, compare, or a free-text question")
    commands.add_parser("compare", help="Run every architecture on every preset")
    return parser


def _runners(config: Config) -> dict[str, RunArchitecture]:
    tools = build_mock_tools()
    trace = ConsoleTrace()

    async def single_loop(question: str) -> ArchitectureResult:
        use_case = SingleAgentLoop(OpenAIChatLLM(config.api_key, config.model), tools, trace, InMemoryMetrics())
        return await use_case.run(question)

    async def orchestrator(question: str) -> ArchitectureResult:
        use_case = OrchestrateWorkers(OrchestratorAdapter(config.model, tools, trace, InMemoryMetrics()))
        return await use_case.run(question)

    async def handoff_flow(question: str) -> ArchitectureResult:
        use_case = TriageAndHandoff(HandoffAdapter(config.model, tools, trace, InMemoryMetrics()))
        return await use_case.run(question)

    return {"single-loop": single_loop, "orchestrator": orchestrator, "handoff": handoff_flow}


def _print_result(result: ArchitectureResult) -> None:
    print(f"\nAnswer ({result.final_agent}): {result.answer}")
    print("agent                        tokens   cost USD   latency ms")
    for metric in result.metrics:
        cost = "n/a" if metric.cost_usd is None else f"{metric.cost_usd:.6f}"
        print(f"{metric.agent:28} {metric.total_tokens:7}   {cost:>8}   {metric.latency_ms:10.1f}")


async def _compare(runners: dict[str, RunArchitecture]) -> None:
    results: list[tuple[str, ArchitectureResult]] = []
    for task in TASKS:
        for name, run in runners.items():
            print(f"\n=== {task.id} / {name} ===")
            result = await run(task.question)
            _print_result(result)
            results.append((task.id, result))
    print("\nTwo-axis map (observed runs)")
    print("single-loop   control=central      context=one growing window")
    print("orchestrator  control=central      context=isolated worker summaries")
    print("handoff       control=transferred  context=filtered conversation history")
    print(f"completed {len(results)} runs; costs are estimates and the provider bill is authoritative")


async def _run(args: argparse.Namespace) -> None:
    if args.command == "tasks":
        for task in TASKS:
            print(f"{task.id:14} {task.question}")
        return
    runners = _runners(Config.from_env())
    if args.command == "compare":
        await _compare(runners)
        return
    result = await runners[args.command](resolve_task(args.task).question)
    _print_result(result)


def main() -> None:
    asyncio.run(_run(build_parser().parse_args()))


if __name__ == "__main__":
    main()
