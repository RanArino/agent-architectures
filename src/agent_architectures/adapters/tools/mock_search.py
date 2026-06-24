from dataclasses import dataclass


WEB_RESULT = "Web: Agent loops alternate model decisions and tool execution until a final answer."
WIKIPEDIA_RESULT = "Wikipedia: An intelligent agent perceives its environment and acts toward goals."


@dataclass(frozen=True)
class MockSearchTool:
    name: str
    description: str
    canned_result: str

    async def execute(self, query: str) -> str:
        return f'{self.canned_result} Query: "{query}".'


def build_mock_tools() -> tuple[MockSearchTool, MockSearchTool]:
    return (
        MockSearchTool("search_web", "Search a mocked web index.", WEB_RESULT),
        MockSearchTool("search_wikipedia", "Search mocked Wikipedia.", WIKIPEDIA_RESULT),
    )

