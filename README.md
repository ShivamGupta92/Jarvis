# Jarvis

A voice-activated conversational assistant for Windows. Say "Jarvis", talk to it, get spoken replies. Built in phases; extensible with tools.

**Stack:** Porcupine (wake word) → Vosk (speech-to-text) → Gemini (brain, provider-abstracted) → Edge-TTS (voice). Wake word and STT run offline; the brain and voice use cloud services.

## Setup (Windows)

1. **Python 3.11+** installed and on PATH.

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Secrets** — copy the template and fill in your keys:
   ```powershell
   copy .env.example .env
   ```
   - `GEMINI_API_KEY` — free tier at https://aistudio.google.com/apikey
   - `PORCUPINE_ACCESS_KEY` — free tier at https://console.picovoice.ai/ (only needed at Phase 3)

5. **Vosk model** (only needed at Phase 2) — download a small English model and unzip it into `models/`:
   - Get `vosk-model-small-en-us-0.15` from https://alphacephei.com/vosk/models
   - Unzip so the path matches `stt.model_path` in `config.yaml`.

6. **Run:**
   ```powershell
   python -m jarvis.main
   ```

## Configuration

All tunable settings live in `config.yaml` (wake word, STT model path, LLM provider/model, TTS voice, conversation timeouts). Secrets live in `.env`. See `config.yaml` for inline documentation of each option.

To change the assistant's voice, list available Edge-TTS voices with `edge-tts --list-voices` and set `tts.voice`.

## Switching the LLM provider

Gemini is the default. The brain sits behind an `LLMProvider` interface, so adding another provider (OpenAI, Anthropic) is a drop-in: implement one engine class, register it in the factory, set `llm.provider` in `config.yaml`. 

## Project layout

See `ARCHITECTURE.md` for the full design and conventions.

