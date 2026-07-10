"""TTSEngine ABC."""

from abc import ABC, abstractmethod


class TTSEngine(ABC):
    """Text-to-speech."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Speak the text aloud, blocking until playback finishes."""
        raise NotImplementedError
