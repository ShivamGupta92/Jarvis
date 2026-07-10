"""GeminiProvider — the brain, running the tool-calling agent loop (§4):

    transcript + tool declarations -> Gemini
      -> function call?  execute via ToolRegistry, append the function
         response to history, call Gemini again (capped iterations)
      -> plain text      that is the spoken reply

Depends only on the ToolRegistry interface — never on a concrete tool.
"""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types

from ..config import LLMSettings
from ..interfaces import LLMProvider, Message, ToolRegistry

TOOL_BUDGET_REPLY = (
    "I had to stop because that request needed more tool steps than I'm allowed. "
    "Try breaking it into smaller requests."
)

# google-genai's Schema type wants uppercase type names; the registry keeps
# declarations in standard JSON schema, so convert at this boundary.
_JSON_SCHEMA_KEYS_TO_RECURSE = ("properties", "items")


def _to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    converted = dict(schema)
    if isinstance(converted.get("type"), str):
        converted["type"] = converted["type"].upper()
    if isinstance(converted.get("properties"), dict):
        converted["properties"] = {
            key: _to_gemini_schema(value) for key, value in converted["properties"].items()
        }
    if isinstance(converted.get("items"), dict):
        converted["items"] = _to_gemini_schema(converted["items"])
    return converted


class GeminiProvider(LLMProvider):
    def __init__(self, settings: LLMSettings, registry: ToolRegistry | None = None) -> None:
        if not settings.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        self._client = genai.Client(api_key=settings.api_key)
        self._model = settings.model
        self._max_tool_iterations = settings.max_tool_iterations
        self._registry = registry

        gemini_tools = None
        if registry is not None:
            declarations = [
                types.FunctionDeclaration(
                    name=d["name"],
                    description=d["description"],
                    parameters=_to_gemini_schema(d["parameters"]),
                )
                for d in registry.declarations()
            ]
            if declarations:
                gemini_tools = [types.Tool(function_declarations=declarations)]

        self._config = types.GenerateContentConfig(
            system_instruction=settings.system_prompt or None,
            tools=gemini_tools,
        )
        self._contents: list[types.Content] = []
        self._transcript: list[Message] = []

    def reply(self, user_text: str) -> str:
        self._contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
        )
        self._transcript.append(Message(role="user", content=user_text))

        text = self._agent_loop()

        self._transcript.append(Message(role="assistant", content=text))
        return text

    def _agent_loop(self) -> str:
        for _ in range(self._max_tool_iterations + 1):
            response = self._client.models.generate_content(
                model=self._model,
                contents=self._contents,
                config=self._config,
            )
            model_content, function_calls, text = self._unpack(response)
            self._contents.append(model_content)

            if not function_calls:
                return text

            if self._registry is None:  # should not happen: no tools were declared
                return text or TOOL_BUDGET_REPLY

            response_parts = []
            for call in function_calls:
                result = self._registry.execute(call.name or "", dict(call.args or {}))
                print(f"  [tool] {call.name}({dict(call.args or {})}) -> "
                      f"{'ok' if result.success else 'error'}")
                response_parts.append(
                    types.Part.from_function_response(
                        name=call.name or "", response=result.for_llm()
                    )
                )
            self._contents.append(types.Content(role="user", parts=response_parts))

        return TOOL_BUDGET_REPLY

    @staticmethod
    def _unpack(
        response: types.GenerateContentResponse,
    ) -> tuple[types.Content, list[types.FunctionCall], str]:
        """Pull the model's content, any function calls, and any text out of
        a response without tripping the SDK's .text warnings."""
        candidate = (response.candidates or [None])[0]
        if candidate is None or candidate.content is None:
            return types.Content(role="model", parts=[]), [], ""
        parts = candidate.content.parts or []
        calls = [p.function_call for p in parts if p.function_call is not None]
        text = "\n".join(p.text for p in parts if p.text).strip()
        return candidate.content, calls, text

    def reset(self) -> None:
        self._contents.clear()
        self._transcript.clear()

    def history(self) -> list[Message]:
        return list(self._transcript)
