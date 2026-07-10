"""VoskSTT — offline speech-to-text via Vosk (Kaldi)."""

from __future__ import annotations

import json

from vosk import KaldiRecognizer, Model, SetLogLevel

from ..config import STTSettings
from ..interfaces import STTEngine
from .audio import record_utterance


class VoskSTT(STTEngine):
    def __init__(self, settings: STTSettings, no_speech_timeout: float) -> None:
        model_path = settings.vosk_model_path
        if not model_path.is_dir():
            raise RuntimeError(
                f"Vosk model not found at '{model_path}'. Download "
                "vosk-model-small-en-us-0.15 from https://alphacephei.com/vosk/models "
                "and unzip it into models/, or point stt.vosk_model_path at it."
            )
        SetLogLevel(-1)  # silence Kaldi's stderr chatter
        self._model = Model(str(model_path))
        self._sample_rate = settings.sample_rate
        self._no_speech_timeout = no_speech_timeout

    def listen(self) -> str:
        print("(listening...)")
        pcm = record_utterance(self._sample_rate, self._no_speech_timeout)
        if not pcm:
            return ""
        recognizer = KaldiRecognizer(self._model, self._sample_rate)
        recognizer.AcceptWaveform(pcm)
        text = json.loads(recognizer.FinalResult()).get("text", "").strip()
        if text:
            print(f"You (heard): {text}")
        return text
