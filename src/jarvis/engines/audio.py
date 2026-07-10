"""Shared microphone/speaker plumbing for the audio engines.

Lives in engines/ because it touches sounddevice/numpy. Playback blocks
until done; recording does simple energy-based endpointing so the STT
engines receive one utterance at a time.
"""

from __future__ import annotations

import numpy as np
import sounddevice as sd


def play_pcm16(pcm: bytes, sample_rate: int, channels: int = 1) -> None:
    """Play signed 16-bit little-endian PCM and block until it finishes."""
    if not pcm:
        return
    samples = np.frombuffer(pcm, dtype=np.int16)
    if channels > 1:
        samples = samples.reshape(-1, channels)
    sd.play(samples, samplerate=sample_rate)
    sd.wait()


def record_utterance(
    sample_rate: int,
    no_speech_timeout: float,
    end_silence_seconds: float = 1.2,
    max_utterance_seconds: float = 30.0,
) -> bytes:
    """Record one spoken utterance from the default microphone.

    Waits up to no_speech_timeout for speech to start (returns b"" if it
    never does), then records until end_silence_seconds of quiet or the
    max utterance length. Returns 16-bit mono PCM at sample_rate.
    """
    frame_seconds = 0.03
    frame_len = int(sample_rate * frame_seconds)

    ambient_frames: list[float] = []
    speech_frames: list[bytes] = []
    speech_started = False
    silent_time = 0.0
    waited = 0.0
    recorded = 0.0

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16") as stream:
        while True:
            data, _overflowed = stream.read(frame_len)
            mono = data[:, 0]
            rms = float(np.sqrt(np.mean(mono.astype(np.float64) ** 2)))

            # Calibrate a speech threshold from the first few ambient frames.
            if len(ambient_frames) < 10 and not speech_started:
                ambient_frames.append(rms)
            ambient = float(np.median(ambient_frames)) if ambient_frames else 0.0
            threshold = max(300.0, ambient * 3.5)

            if not speech_started:
                waited += frame_seconds
                if rms >= threshold:
                    speech_started = True
                    speech_frames.append(mono.tobytes())
                elif waited >= no_speech_timeout:
                    return b""
                continue

            speech_frames.append(mono.tobytes())
            recorded += frame_seconds
            silent_time = silent_time + frame_seconds if rms < threshold else 0.0
            if silent_time >= end_silence_seconds or recorded >= max_utterance_seconds:
                return b"".join(speech_frames)
