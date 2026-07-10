"""WhisperSTT — offline speech-to-text via faster-whisper."""

from __future__ import annotations

import numpy as np
from faster_whisper import WhisperModel

from ..config import STTSettings
from ..interfaces import STTEngine
from .audio import record_utterance


class WhisperSTT(STTEngine):
    def __init__(self, settings: STTSettings, no_speech_timeout: float) -> None:
        # int8 on CPU keeps the base model fast enough for conversation.
        self._model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        self._sample_rate = settings.sample_rate
        self._no_speech_timeout = no_speech_timeout

    def listen(self) -> str:
        print("(listening...)")
        pcm = record_utterance(self._sample_rate, self._no_speech_timeout)
        if not pcm:
            return ""
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _info = self._model.transcribe(audio, language="en", beam_size=5)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if text:
            print(f"You (heard): {text}")
        return text
