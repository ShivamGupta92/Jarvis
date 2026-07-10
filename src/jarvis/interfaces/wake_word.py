"""WakeWordDetector ABC."""

from abc import ABC, abstractmethod


class WakeWordDetector(ABC):
    """Blocks until the wake word is heard."""

    @abstractmethod
    def wait_for_wake(self) -> None:
        """Block until the wake word is detected, then return."""
        raise NotImplementedError
