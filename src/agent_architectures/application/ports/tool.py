from typing import Protocol


class ToolPort(Protocol):
    name: str
    description: str

    async def execute(self, query: str) -> str: ...

