from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    instructions: str
    tool_names: tuple[str, ...] = ()

