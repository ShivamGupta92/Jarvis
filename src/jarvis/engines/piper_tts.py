"""PiperTTS — fully offline TTS from a local .onnx voice model."""

from __future__ import annotations

from piper import PiperVoice

from ..config import TTSSettings
from ..interfaces import TTSEngine
from .audio import play_pcm16


class PiperTTS(TTSEngine):
    def __init__(self, settings: TTSSettings) -> None:
        model = settings.piper_model
        if not model.is_file():
            raise RuntimeError(
                f"Piper model not found at '{model}'. Download a voice (e.g. "
                "en_US-lessac-medium.onnx plus its .json) into models/piper/ "
                "or point tts.piper_model in config.yaml at it."
            )
        self._voice = PiperVoice.load(str(model))

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        if hasattr(self._voice, "synthesize_stream_raw"):  # piper-tts <= 1.2
            pcm = b"".join(self._voice.synthesize_stream_raw(text))
            rate = self._voice.config.sample_rate
        else:  # piper-tts >= 1.3 yields AudioChunk objects
            chunks = list(self._voice.synthesize(text))
            if not chunks:
                return
            pcm = b"".join(c.audio_int16_bytes for c in chunks)
            rate = chunks[0].sample_rate
        play_pcm16(pcm, rate)
