"""Entry point + factory. Reads config/.env, constructs the matching
concrete engines, and hands them to the Assistant. Engine modules are
imported lazily so a mode only needs its own dependencies installed.

Run modes (map to the build phases, useful forever for debugging):
  --mode text   typed input, printed replies            (Phases 0-1)
  --mode type   typed input, spoken replies             (Phase 2)
  --mode talk   spoken input, spoken replies, no wake   (Phase 3)
  --mode voice  full Jarvis: wake word + voice          (Phase 4, default)
"""

from __future__ import annotations

import argparse
import sys

from .assistant import Assistant
from .config import Settings, load_settings
from .interfaces import LLMProvider, STTEngine, ToolRegistry, TTSEngine, WakeWordDetector


def _build_llm(settings: Settings, registry: ToolRegistry) -> LLMProvider:
    if settings.llm.provider != "gemini":
        raise ValueError(f"Unknown llm.provider '{settings.llm.provider}' (only 'gemini' in v1)")
    from .engines.gemini_llm import GeminiProvider

    return GeminiProvider(settings.llm, registry)


def _build_tts(settings: Settings) -> TTSEngine:
    if settings.tts.provider == "edge":
        from .engines.edge_tts import EdgeTTS

        return EdgeTTS(settings.tts)
    if settings.tts.provider == "piper":
        from .engines.piper_tts import PiperTTS

        return PiperTTS(settings.tts)
    raise ValueError(f"Unknown tts.provider '{settings.tts.provider}' (edge | piper)")


def _build_stt(settings: Settings) -> STTEngine:
    raise NotImplementedError("Voice input arrives in Phase 3. Run with --mode text.")


def _build_wake(settings: Settings) -> WakeWordDetector:
    raise NotImplementedError("The wake word arrives in Phase 4. Run with --mode text.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="jarvis", description="Jarvis voice assistant")
    parser.add_argument(
        "--mode",
        choices=["text", "type", "talk", "voice"],
        default="voice",
        help="text: typed in/out; type: typed in, spoken out; "
        "talk: voice in/out without wake word; voice: full Jarvis (default)",
    )
    parser.add_argument("--config", default="config.yaml", help="path to config.yaml")
    args = parser.parse_args()

    settings = load_settings(args.config)

    from .engines.console import ConsoleSTT, ConsoleTTS, ConsoleWake
    from .tools import build_registry

    try:
        registry = build_registry(settings.tools)
        llm = _build_llm(settings, registry)
        tts = ConsoleTTS() if args.mode == "text" else _build_tts(settings)
        stt = ConsoleSTT() if args.mode in ("text", "type") else _build_stt(settings)
        wake = ConsoleWake() if args.mode != "voice" else _build_wake(settings)
    except (NotImplementedError, RuntimeError, ValueError) as exc:
        print(f"jarvis: {exc}", file=sys.stderr)
        sys.exit(1)

    Assistant(wake, stt, llm, tts, settings.conversation).run()


if __name__ == "__main__":
    main()
