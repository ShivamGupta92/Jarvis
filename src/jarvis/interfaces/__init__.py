"""Abstract interfaces. The orchestrator depends on these and nothing else."""

from .llm import LLMProvider, Message
from .stt import STTEngine
from .tools import Tool, ToolRegistry, ToolResult
from .tts import TTSEngine
from .wake_word import WakeWordDetector

__all__ = [
    "LLMProvider",
    "Message",
    "STTEngine",
    "Tool",
    "ToolRegistry",
    "ToolResult",
    "TTSEngine",
    "WakeWordDetector",
]
