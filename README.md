# Jarvis

A voice-activated desktop assistant for **Windows** that can act on your PC. Say "Jarvis" → it wakes → you speak → it answers **and can execute tools**: create folders, write and read files, summarize documents, and locate files — all confined to an allowlisted workspace.

**Stack:** Porcupine (wake word, offline) → faster-whisper **or** Vosk (STT, offline, switchable) → Gemini function calling (brain + tools, provider-abstracted) → Edge-TTS **or** Piper (TTS, switchable).

The full design, safety model, and conventions live in [`JARVIS.md`](JARVIS.md) — the source of truth this project is built from.

## Setup (Windows)

1. **Python 3.11+** installed and on PATH.

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies and the package:**
   ```powershell
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Secrets** — copy the template and fill in your keys:
   ```powershell
   copy .env.example .env
   ```
   - `GEMINI_API_KEY` — free tier at https://aistudio.google.com/apikey
   - `PORCUPINE_ACCESS_KEY` — free tier at https://console.picovoice.ai/ (only needed for the wake word)
   - `STT_PROVIDER` — `faster_whisper` (default; auto-downloads its model on first run) or `vosk`

5. **Offline models** (only for the engines you choose):
   - **Vosk** (if `STT_PROVIDER=vosk`): download `vosk-model-small-en-us-0.15` from https://alphacephei.com/vosk/models and unzip into `models/` so it matches `stt.vosk_model_path` in `config.yaml`.
   - **Piper** (if `tts.provider: piper`): `python -m piper.download_voices en_US-lessac-medium` into `models/piper/`, matching `tts.piper_model`.

6. **Run:**
   ```powershell
   python -m jarvis.main
   ```

## Run modes

The full voice pipeline is the default, but every earlier build phase remains runnable — useful for testing the brain and tools without a microphone:

| Command | Input | Output | Wake word |
|---|---|---|---|
| `python -m jarvis.main --mode text` | typed | printed | no |
| `python -m jarvis.main --mode type` | typed | spoken | no |
| `python -m jarvis.main --mode talk` | spoken | spoken | no |
| `python -m jarvis.main` (voice) | spoken | spoken | **yes** |

In typed modes, enter `quit` (or Ctrl+C) to exit. Saying/typing a sleep phrase ("goodbye", "go to sleep", "stop listening") ends the conversation; silence does too.

## Tools and safety

Jarvis's five tools — `create_folder`, `write_file`, `read_file`, `summarize_document`, `find_file` — only ever touch the filesystem through `_safe_path`, which resolves every path and rejects anything outside the workspace root (`tools.workspace_root` in `config.yaml`, default `~/JarvisWorkspace`). `find_file` additionally searches only the allowlisted roots in `tools.find_search_roots` and caps its results. `write_file` never overwrites silently. There are no delete/move/rename tools in v1, by design.

## Configuration

Tunables live in `config.yaml` (wake word sensitivity, STT/TTS models and voices, LLM model, tool workspace, timeouts); secrets and the STT switch live in `.env`. Only `src/jarvis/config.py` reads either.

- Change the spoken voice: `edge-tts --list-voices`, then set `tts.edge_voice`.
- Go fully offline for speech: `tts.provider: piper` + `STT_PROVIDER=vosk` (or `faster_whisper` after its first model download).

## Switching the LLM provider

Gemini is the only provider wired in v1, but the brain sits behind an `LLMProvider` interface that owns the tool-calling agent loop. Adding another provider is a drop-in: implement one engine class in `src/jarvis/engines/`, register it in the `main.py` factory, and set `llm.provider` in `config.yaml`.

## Project layout

```
src/jarvis/
├── main.py         # factory: builds engines + tools from config, runs Assistant
├── assistant.py    # orchestrator; depends only on the interfaces
├── config.py       # .env + config.yaml -> typed Settings
├── interfaces/     # WakeWordDetector, STTEngine, LLMProvider, TTSEngine, ToolRegistry
├── engines/        # the ONLY place third-party SDKs are imported
└── tools/          # _safe_path guard, registry, and the five v1 tools
```
