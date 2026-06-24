import json
from collections.abc import Sequence

from openai import AsyncOpenAI

from ...application.ports import LLMResponse, ToolCall, ToolPort
from ...domain import Message
from ...pricing import estimate_cost_usd


class OpenAIChatLLM:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(self, messages: Sequence[Message], tools: Sequence[ToolPort]) -> LLMResponse:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=self._to_openai_messages(messages),  # type: ignore[arg-type]
            tools=[self._tool_schema(tool) for tool in tools],  # type: ignore[arg-type]
            tool_choice="auto",
        )
        message = response.choices[0].message
        calls = tuple(
            ToolCall(call.id, call.function.name, json.loads(call.function.arguments))
            for call in message.tool_calls or ()
        )
        usage = response.usage
        return LLMResponse(
            content=message.content or "",
            tool_calls=calls,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            cost_usd=estimate_cost_usd(
                self._model,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
            ),
        )

    @staticmethod
    def _tool_schema(tool: ToolPort) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }

    @staticmethod
    def _to_openai_messages(messages: Sequence[Message]) -> list[dict[str, object]]:
        converted: list[dict[str, object]] = []
        for message in messages:
            if message.role == "assistant" and message.content.startswith("["):
                calls = json.loads(message.content)
                converted.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": call["id"],
                        "type": "function",
                        "function": {"name": call["name"], "arguments": json.dumps(call["arguments"])},
                    } for call in calls],
                })
            elif message.role == "tool":
                converted.append({"role": "tool", "content": message.content, "tool_call_id": message.tool_call_id})
            else:
                converted.append({"role": message.role, "content": message.content})
        return converted
