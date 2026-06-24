from .domain import Task


TASKS = (
    Task("plain", "Explain an AI agent loop in one sentence without using tools."),
    Task("single-source", "According to Wikipedia, what is an intelligent agent?"),
    Task("compare", "Compare what the web and Wikipedia say about AI agents."),
)


def resolve_task(value: str) -> Task:
    return next((task for task in TASKS if task.id == value), Task("custom", value))

