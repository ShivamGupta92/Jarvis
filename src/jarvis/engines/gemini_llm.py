"""GeminiProvider — the brain. Phase 0: single-shot chat with in-session
history. Phase 1 upgrades this to the tool-calling agent loop.
"""

from __future__ import annotations

from google import genai
from google.genai import types

from ..config import LLMSettings
from ..interfaces import LLMProvider, Message


class GeminiProvider(LLMProvider):
    def __init__(self, settings: LLMSettings) -> None:
        if not settings.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        self._client = genai.Client(api_key=settings.api_key)
        self._model = settings.model
        self._config = types.GenerateContentConfig(
            system_instruction=settings.system_prompt or None,
        )
        self._contents: list[types.Content] = []
        self._transcript: list[Message] = []

    def reply(self, user_text: str) -> str:
        self._contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
        )
        self._transcript.append(Message(role="user", content=user_text))

        response = self._client.models.generate_content(
            model=self._model,
            contents=self._contents,
            config=self._config,
        )
        text = (response.text or "").strip()

        self._contents.append(
            types.Content(role="model", parts=[types.Part.from_text(text=text)])
        )
        self._transcript.append(Message(role="assistant", content=text))
        return text

    def reset(self) -> None:
        self._contents.clear()
        self._transcript.clear()

    def history(self) -> list[Message]:
        return list(self._transcript)
