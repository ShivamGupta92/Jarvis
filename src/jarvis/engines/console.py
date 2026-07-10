"""Console stand-ins for the audio engines, used by the text/type/talk
run modes so the brain and tools can be tested without any audio stack.
"""

from ..interfaces import STTEngine, TTSEngine, WakeWordDetector

QUIT_WORDS = {"quit", "exit"}


class ConsoleWake(WakeWordDetector):
    """No wake word: every conversation starts immediately."""

    def __init__(self) -> None:
        self._first = True

    def wait_for_wake(self) -> None:
        if self._first:
            print("(no wake word in this mode — conversation starts now; "
                  "type 'quit' or press Ctrl+C to exit)")
            self._first = False
        else:
            print("(new conversation)")


class ConsoleSTT(STTEngine):
    """Typed input instead of a microphone."""

    def listen(self) -> str:
        line = input("You: ")
        if line.strip().lower() in QUIT_WORDS:
            raise EOFError
        return line


class ConsoleTTS(TTSEngine):
    """Printed replies instead of a speaker."""

    def speak(self, text: str) -> None:
        print(f"Jarvis: {text}")
