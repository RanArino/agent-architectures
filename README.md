# Agent Architectures

*日本語版: [README-ja.md](README-ja.md)*

This PoC asks: **what changes when the same task runs through a single agent loop, an
orchestrator with isolated workers, or a handoff?** The hypothesis is that running the
three flows side by side makes control location and context ownership easier to understand
than diagrams alone.

It uses real OpenAI model calls and the real OpenAI Agents SDK primitives, but both search
tools return local canned text. It never calls a search service or a Scaler environment.

## Prerequisites

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- `OPENAI_API_KEY` for architecture runs (`tasks` and the test suite need no key)
- Optional `OPENAI_MODEL`; the default is `gpt-4.1-mini`

### Set your API key

Copy the example file and fill in your key (`.env` is gitignored):

```bash
cp .env.example .env
# then edit .env and set OPENAI_API_KEY
```

Both `agentflow` and `agentflow-ui` load `.env` automatically. If you prefer,
`export OPENAI_API_KEY="..."` in your shell works too and takes precedence over `.env`.

## Run it

From this directory:

```bash
uv sync --extra dev
uv run agentflow tasks
uv run agentflow single-loop plain
uv run agentflow orchestrator single-source
uv run agentflow handoff compare
uv run agentflow compare
```

The task argument can be `plain`, `single-source`, `compare`, or a free-text question.
`compare` performs nine live model runs: every architecture over every preset. Each run
prints the post-filter input sent on every SDK model call, response-local token use,
estimated cost, and model latency. Repeated model calls are aggregated by agent without
counting nested workers in the manager's totals. The default model estimate
uses the [published GPT-4.1 mini token rates](https://platform.openai.com/docs/models/gpt-4.1-mini)
checked on 2026-06-24 and conservatively ignores cached-token discounts. Cost is `n/a` for
an unrecognized `OPENAI_MODEL`; the provider's bill remains authoritative.

Run all key-free checks with:

```bash
uv run pytest -q
```

## Visual UI (local)

A local web UI draws each architecture as a swimlane timeline — context windows growing,
summaries/handoffs crossing between agents, and who owns the final answer — for people
meeting multi-agent orchestration for the first time. The backend (`web.py`) is a second
composition root that runs the real use cases with a data-collecting trace; the frontend is
one static `index.html` (vanilla JS, no build step), served by the backend.

```bash
uv sync --extra ui
uv run agentflow-ui           # http://127.0.0.1:8000
```

Live runs need `OPENAI_API_KEY` (set it in `.env` as above); the page loads without one.

Pick a task, then run one architecture or **Run all three (compare)**. Binds to
`127.0.0.1` only; `AGENTFLOW_UI_HOST` / `AGENTFLOW_UI_PORT` override host/port.

## Try your own tasks

The preset tasks (`plain`, `single-source`, `compare`) are intentionally short, single-turn
questions. They make the control structure easy to see, but they are not long enough to show
where the orchestrator's isolation advantage actually pays off — parallel delegation and summary
compression only matter when the single loop's context starts to bloat.

**Quick way — pass a free-text question directly:**

```bash
uv run agentflow single-loop "Research the differences between symbolic AI and neural networks from multiple angles."
uv run agentflow orchestrator "Research the differences between symbolic AI and neural networks from multiple angles."
uv run agentflow handoff "Research the differences between symbolic AI and neural networks from multiple angles."
```

**Deeper way — add a named preset in `src/agent_architectures/fixtures.py`:**

```python
Task("my-task", "Your longer, multi-step question here."),
```

Then run `uv run agentflow compare my-task` to see all three architectures on the same input.

**What makes a task reveal the differences:**

| Task shape | What it stresses |
|---|---|
| Short, single-source | All three look similar; single loop has least overhead |
| Multi-source, compare both | Orchestrator's worker isolation starts to matter; single loop accumulates raw tool results |
| Long, multi-step synthesis | Single loop's context window grows fastest; orchestrator's summaries keep the manager window small; handoff's input filter becomes significant |

The honest limit of the current PoC: tool results are canned local text, so token counts are
small regardless. For a real comparison, replace the canned tools with live search and give
the model a question that requires several round trips.

## What is implemented

| Command | Control | Context ownership | Primitive |
|---|---|---|---|
| `single-loop` | One agent | One window accumulates raw tool results | Raw OpenAI client |
| `orchestrator` | Manager retains control | Workers receive structured tasks and return summaries | `Agent.as_tool()` |
| `handoff` | Triage transfers control | Receiver inherits filtered dialogue and gives the final answer | `handoff()` + `input_filter` |

The single loop explicitly performs model → tool → model turns. The orchestrator owns only
worker-tools; each source worker owns only its source tool. Delegation uses a structured
`TaskDescription` (`objective`, `output_format`, `allowed_tools`, and `boundaries`). The
handoff flow has source specialists plus a two-source comparison specialist, and removes
tool traffic when control crosses the boundary.

The application core depends on small LLM, tool, trace, metrics, and orchestration ports.
The raw OpenAI client and Agents SDK live in adapters; `cli.py` is the composition root.
This boundary makes the plain loop's model provider replaceable. The honest limit is that
the SDK adapters own most of the M2/M3 flow because the SDK itself is the orchestrator.

Official references: [Python Agents SDK](https://openai.github.io/openai-agents-python/),
[tools and agents-as-tools](https://openai.github.io/openai-agents-python/tools/),
[handoffs and input filters](https://openai.github.io/openai-agents-python/handoffs/), and
[usage](https://openai.github.io/openai-agents-python/usage/).

## Conclusion

**Keep as a concluded learning artifact; do not graduate it into production as-is.** It
demonstrates the intended architecture contrasts with minimal deterministic tools. A real
feature should reuse the learned control/context choices, not copy this PoC's canned data,
prompts, or CLI.

## What running this taught me about agent flow

An agent loop is small: the model chooses an action, the application executes it, and the
result becomes the next model input. Multi-agent architecture mainly changes who chooses
the next action and which history they can see. Agents-as-tools are a strong fit for
backstage work because the manager keeps control and summaries form a narrow interface.
Handoffs fit user-facing ownership because the receiver becomes responsible for the final
answer. Context isolation is useful, but it is not free: delegation prompts and summaries
become contracts that must be designed and observed.
