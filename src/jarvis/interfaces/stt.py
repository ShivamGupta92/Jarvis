"""STTEngine ABC."""

from abc import ABC, abstractmethod


class STTEngine(ABC):
    """Speech-to-text. Capture and transcription both live behind this
    interface because audio I/O requires third-party SDKs, which are
    confined to engines/ — the orchestrator never touches a microphone.
    """

    @abstractmethod
    def listen(self) -> str:
        """Record one utterance from the microphone and return its transcript.

        Returns an empty string if no speech is heard before the
        configured silence timeout.
        """
        raise NotImplementedError
