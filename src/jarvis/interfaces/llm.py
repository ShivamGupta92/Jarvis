"""LLMProvider ABC (+ Message type).

The provider is the brain. It owns the in-session conversation memory and
(from Phase 1) the tool-calling agent loop: it keeps calling the model,
executing requested tools through a ToolRegistry, and feeding results back
until the model produces plain text — which is the spoken reply.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    """One turn of the generic conversation transcript."""

    role: str  # "user" | "assistant"
    content: str


class LLMProvider(ABC):
    @abstractmethod
    def reply(self, user_text: str) -> str:
        """Send one user turn, run the agent loop to completion, and return
        the final text reply. Conversation memory persists across calls
        until reset() — and is never persisted across process runs.
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Discard the in-session conversation memory."""
        raise NotImplementedError

    @abstractmethod
    def history(self) -> list[Message]:
        """The generic user/assistant transcript (for logging/debugging)."""
        raise NotImplementedError
