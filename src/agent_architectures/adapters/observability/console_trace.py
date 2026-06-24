from collections.abc import Sequence
from typing import TextIO
import sys

from ...domain import Message


class ConsoleTrace:
    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream or sys.stdout

    def context(self, agent: str, messages: Sequence[Message]) -> None:
        print(f"\n[{agent}] context ({len(messages)} messages)", file=self._stream)
        for message in messages:
            label = f"/{message.name}" if message.name else ""
            print(f"  {message.role}{label}: {message.content}", file=self._stream)

    def event(self, agent: str, event: str, detail: str) -> None:
        print(f"[{agent}] {event}: {detail}", file=self._stream)

