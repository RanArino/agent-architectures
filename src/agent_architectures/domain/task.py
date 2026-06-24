from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: str
    question: str


@dataclass(frozen=True)
class TaskDescription:
    objective: str
    output_format: str
    allowed_tools: tuple[str, ...]
    boundaries: str

    def as_prompt(self) -> str:
        tools = ", ".join(self.allowed_tools) or "none"
        return (
            f"Objective: {self.objective}\nOutput: {self.output_format}\n"
            f"Allowed tools: {tools}\nBoundaries: {self.boundaries}"
        )

