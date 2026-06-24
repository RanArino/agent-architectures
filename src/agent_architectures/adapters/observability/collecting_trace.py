from collections.abc import Sequence

from ...domain import Message


class CollectingTrace:
    """A TracePort that records the flow as structured steps instead of printing it.

    Same observations as ConsoleTrace — each agent's context window plus the discrete
    events between model calls — but captured as plain data so a UI can draw the flow.
    Swapping ConsoleTrace for this is the whole change needed to feed the visualizer:
    the use cases never know which TracePort is plugged in.
    """

    def __init__(self) -> None:
        self._steps: list[dict[str, object]] = []

    def context(self, agent: str, messages: Sequence[Message]) -> None:
        rendered = [{"role": message.role, "name": message.name, "content": message.content} for message in messages]
        approx_tokens = sum(max(1, len(message.content) // 4) for message in messages)
        self._steps.append({
            "seq": len(self._steps),
            "kind": "context",
            "agent": agent,
            "messages": rendered,
            "count": len(rendered),
            "approx_tokens": approx_tokens,
        })

    def event(self, agent: str, event: str, detail: str) -> None:
        self._steps.append({
            "seq": len(self._steps),
            "kind": "event",
            "agent": agent,
            "event": event,
            "detail": detail,
        })

    def steps(self) -> list[dict[str, object]]:
        return self._steps
