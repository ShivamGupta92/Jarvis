"""PorcupineWake — offline wake-word detection via Picovoice Porcupine.

Feeds microphone frames (int16, porcupine.frame_length samples at
porcupine.sample_rate) to the detector and returns when the keyword is
heard.
"""

from __future__ import annotations

import pvporcupine
import sounddevice as sd

from ..config import WakeWordSettings
from ..interfaces import WakeWordDetector


class PorcupineWake(WakeWordDetector):
    def __init__(self, settings: WakeWordSettings) -> None:
        if not settings.access_key:
            raise RuntimeError(
                "PORCUPINE_ACCESS_KEY is not set. Get a free key at "
                "https://console.picovoice.ai/ and add it to .env."
            )
        keyword = settings.keyword.lower()
        if keyword not in pvporcupine.KEYWORDS:
            raise RuntimeError(
                f"'{settings.keyword}' is not a built-in Porcupine keyword. "
                f"Built-ins include: {', '.join(sorted(pvporcupine.KEYWORDS))}."
            )
        self._keyword = keyword
        self._porcupine = pvporcupine.create(
            access_key=settings.access_key,
            keywords=[keyword],
            sensitivities=[settings.sensitivity],
        )

    def wait_for_wake(self) -> None:
        engine = self._porcupine
        print(f'(idle — say "{self._keyword}", Ctrl+C to quit)')
        with sd.InputStream(
            samplerate=engine.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=engine.frame_length,
        ) as stream:
            while True:
                frame, _overflowed = stream.read(engine.frame_length)
                if engine.process(frame[:, 0].tolist()) >= 0:
                    return

    def __del__(self) -> None:
        porcupine = getattr(self, "_porcupine", None)
        if porcupine is not None:
            porcupine.delete()
