"""EdgeTTS — online neural voices via Microsoft Edge's TTS service.
Synthesizes to mp3 in memory, decodes with miniaudio, plays through
sounddevice.
"""

from __future__ import annotations

import asyncio

import edge_tts
import miniaudio

from ..config import TTSSettings
from ..interfaces import TTSEngine
from .audio import play_pcm16


class EdgeTTS(TTSEngine):
    def __init__(self, settings: TTSSettings) -> None:
        self._voice = settings.edge_voice

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        mp3 = asyncio.run(self._synthesize(text))
        decoded = miniaudio.decode(mp3, output_format=miniaudio.SampleFormat.SIGNED16)
        play_pcm16(
            bytes(decoded.samples), decoded.sample_rate, channels=decoded.nchannels
        )

    async def _synthesize(self, text: str) -> bytes:
        stream = edge_tts.Communicate(text, self._voice)
        audio = bytearray()
        async for chunk in stream.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
        if not audio:
            raise RuntimeError("Edge-TTS returned no audio (offline? voice name wrong?).")
        return bytes(audio)
