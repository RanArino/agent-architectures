from dataclasses import dataclass
from typing import Protocol, Sequence

from ...domain import Message
from .tool import ToolPort


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, str]


@dataclass(frozen=True)
class LLMResponse:
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None


class LLMPort(Protocol):
    async def complete(self, messages: Sequence[Message], tools: Sequence[ToolPort]) -> LLMResponse: ...
