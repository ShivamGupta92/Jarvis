"""Concrete engines. This package is the ONLY place third-party SDKs
(google-genai, faster_whisper, vosk, pvporcupine, edge_tts, piper) are
imported. Modules are imported lazily by the factory in main.py so that
running one mode never requires the other modes' dependencies.
"""
