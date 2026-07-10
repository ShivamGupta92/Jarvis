"""The orchestrator. Depends ONLY on the abstract interfaces — it never
imports a concrete engine, an SDK, or a tool.

Lifecycle: idle until the wake word → greet → hold a conversation
(listen → think → speak) → return to idle on silence or a sleep phrase.
In text modes the wake/STT/TTS engines are console stand-ins, so the
same loop serves every phase.
"""

from __future__ import annotations

import traceback

from .config import ConversationSettings
from .interfaces import LLMProvider, STTEngine, TTSEngine, WakeWordDetector

GREETING = "Yes?"
SLEEP_REPLY = "Goodbye."
SILENCE_REPLY = "Going back to sleep."
ERROR_REPLY = "Sorry, something went wrong while I was thinking. Please try again."


class Assistant:
    def __init__(
        self,
        wake: WakeWordDetector,
        stt: STTEngine,
        llm: LLMProvider,
        tts: TTSEngine,
        conversation: ConversationSettings,
    ) -> None:
        self._wake = wake
        self._stt = stt
        self._llm = llm
        self._tts = tts
        self._conversation = conversation

    def run(self) -> None:
        """Main loop: idle → wake → converse → idle. Runs until Ctrl+C
        (or 'quit' in text modes)."""
        try:
            while True:
                self._wake.wait_for_wake()
                self._speak(GREETING)
                self._converse()
        except (EOFError, KeyboardInterrupt):
            print("\nJarvis shutting down.")

    def _converse(self) -> None:
        """One conversation: ends on silence or a sleep phrase."""
        while True:
            heard = self._stt.listen()
            if not heard.strip():
                self._speak(SILENCE_REPLY)
                return
            if self._is_sleep_phrase(heard):
                self._speak(SLEEP_REPLY)
                return

            try:
                reply = self._llm.reply(heard)
            except Exception:
                traceback.print_exc()
                self._speak(ERROR_REPLY)
                continue
            self._speak(reply or "I have nothing to say to that.")

    def _is_sleep_phrase(self, text: str) -> bool:
        lowered = text.lower()
        return any(phrase in lowered for phrase in self._conversation.sleep_phrases)

    def _speak(self, text: str) -> None:
        """Speak, falling back to print if the TTS engine fails (e.g. the
        online voice is unreachable) so a reply is never lost."""
        try:
            self._tts.speak(text)
        except Exception:
            traceback.print_exc()
            print(f"Jarvis (voice unavailable): {text}")
