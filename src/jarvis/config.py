"""Loads .env + config.yaml into a typed Settings object.

This is the ONLY module that reads environment variables or YAML.
Everything else receives a Settings (or a section of it) explicitly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class WakeWordSettings:
    keyword: str = "jarvis"
    sensitivity: float = 0.5
    access_key: str = ""  # from .env: PORCUPINE_ACCESS_KEY


@dataclass(frozen=True)
class STTSettings:
    provider: str = "faster_whisper"  # from .env: STT_PROVIDER (faster_whisper | vosk)
    whisper_model: str = "base"
    vosk_model_path: Path = Path("models/vosk-model-small-en-us-0.15")
    sample_rate: int = 16000


@dataclass(frozen=True)
class LLMSettings:
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"
    max_tool_iterations: int = 5
    system_prompt: str = ""
    api_key: str = ""  # from .env: GEMINI_API_KEY


@dataclass(frozen=True)
class TTSSettings:
    provider: str = "edge"  # edge | piper
    edge_voice: str = "en-US-GuyNeural"
    piper_model: Path = Path("models/piper/en_US-lessac-medium.onnx")


@dataclass(frozen=True)
class ToolsSettings:
    workspace_root: Path = Path("~/JarvisWorkspace")
    find_search_roots: tuple[Path, ...] = ()
    find_max_results: int = 20


@dataclass(frozen=True)
class ConversationSettings:
    silence_timeout_seconds: float = 8.0
    sleep_phrases: tuple[str, ...] = ("go to sleep", "goodbye", "stop listening")


@dataclass(frozen=True)
class Settings:
    wake_word: WakeWordSettings = field(default_factory=WakeWordSettings)
    stt: STTSettings = field(default_factory=STTSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    tts: TTSSettings = field(default_factory=TTSSettings)
    tools: ToolsSettings = field(default_factory=ToolsSettings)
    conversation: ConversationSettings = field(default_factory=ConversationSettings)


def _expand(p: str | Path) -> Path:
    return Path(p).expanduser()


def load_settings(config_path: str | Path = "config.yaml") -> Settings:
    """Read .env (secrets/switches) and config.yaml (tunables) into Settings."""
    load_dotenv()

    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"config.yaml not found at '{path.resolve()}'. "
            "Run from the repository root or pass --config."
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    ww = raw.get("wake_word", {})
    stt = raw.get("stt", {})
    llm = raw.get("llm", {})
    tts = raw.get("tts", {})
    tools = raw.get("tools", {})
    conv = raw.get("conversation", {})

    return Settings(
        wake_word=WakeWordSettings(
            keyword=ww.get("keyword", "jarvis"),
            sensitivity=float(ww.get("sensitivity", 0.5)),
            access_key=os.getenv("PORCUPINE_ACCESS_KEY", ""),
        ),
        stt=STTSettings(
            provider=os.getenv("STT_PROVIDER", "faster_whisper").strip().lower(),
            whisper_model=stt.get("whisper_model", "base"),
            vosk_model_path=_expand(stt.get("vosk_model_path", "models/vosk-model-small-en-us-0.15")),
            sample_rate=int(stt.get("sample_rate", 16000)),
        ),
        llm=LLMSettings(
            provider=llm.get("provider", "gemini"),
            model=llm.get("model", "gemini-2.0-flash"),
            max_tool_iterations=int(llm.get("max_tool_iterations", 5)),
            system_prompt=llm.get("system_prompt", ""),
            api_key=os.getenv("GEMINI_API_KEY", ""),
        ),
        tts=TTSSettings(
            provider=tts.get("provider", "edge"),
            edge_voice=tts.get("edge_voice", "en-US-GuyNeural"),
            piper_model=_expand(tts.get("piper_model", "models/piper/en_US-lessac-medium.onnx")),
        ),
        tools=ToolsSettings(
            workspace_root=_expand(tools.get("workspace_root", "~/JarvisWorkspace")),
            find_search_roots=tuple(_expand(p) for p in tools.get("find_search_roots", [])),
            find_max_results=int(tools.get("find_max_results", 20)),
        ),
        conversation=ConversationSettings(
            silence_timeout_seconds=float(conv.get("silence_timeout_seconds", 8.0)),
            sleep_phrases=tuple(
                str(p).lower() for p in conv.get("sleep_phrases", ["go to sleep", "goodbye"])
            ),
        ),
    )
