from .ports import ArchitectureResult, OrchestratorPort


class TriageAndHandoff:
    def __init__(self, orchestrator: OrchestratorPort) -> None:
        self._orchestrator = orchestrator

    async def run(self, question: str) -> ArchitectureResult:
        return await self._orchestrator.run(question)

