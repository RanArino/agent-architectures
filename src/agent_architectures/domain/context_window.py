from dataclasses import dataclass, field


@dataclass(frozen=True)
class Message:
    role: str
    content: str
    name: str | None = None
    tool_call_id: str | None = None


@dataclass
class ContextWindow:
    owner: str
    messages: list[Message] = field(default_factory=list)

    def add(self, role: str, content: str, **metadata: str) -> None:
        self.messages.append(Message(role=role, content=content, **metadata))

    @property
    def approximate_tokens(self) -> int:
        return sum(max(1, len(message.content) // 4) for message in self.messages)

