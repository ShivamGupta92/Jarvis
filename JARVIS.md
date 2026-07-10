# Jarvis — Architecture & Project Base

A voice-activated desktop assistant for **Windows**. It idles until a wake word, holds a spoken conversation, and can execute **system-level tools** on your PC — create folders, write and read files, summarize documents, and locate files. This document is the single source of truth Fable builds from: it defines the design, the contracts, the safety model, the tool set, and the build order.

---

## 1. Goal

Say "Jarvis" → it wakes → you speak → it answers **and can act on your machine**. Tools are not an afterthought; they are the point of v1. A conversation-only assistant is the fallback if tools are disabled, not the deliverable.

The five v1 tools:

1. `create_folder` — make a directory
2. `write_file` — write a document
3. `read_file` — read a file's contents
4. `summarize_document` — read a document and return a summary
5. `find_file` — locate a file by name on the PC

---

## 2. Stack

| Concern       | Engine(s)                          | Runs           | Selection            |
|---------------|------------------------------------|----------------|----------------------|
| Wake word     | Porcupine                          | Offline        | fixed                |
| STT           | **faster-whisper OR Vosk**         | Offline        | **`.env` switch**    |
| Brain + tools | **Gemini** (function calling)      | Cloud          | config (swappable)   |
| TTS           | **Edge-TTS OR piper**              | Online/Offline | **config switch**    |

Python 3.11+. In-session conversation memory only (discarded on exit). Windows-first: use `pathlib`, never hardcode separators.

**Configurable engines (the two you asked for):**

- **STT** is selectable via `.env` (`STT_PROVIDER=faster_whisper` or `vosk`). Both implement the same `STTEngine` interface; the factory picks one at startup.
- **TTS** is selectable via config (`TTS_PROVIDER=edge` or `piper`). Both implement the same `TTSEngine` interface.

---

## 3. Core architecture — five interfaces

The orchestrator (`assistant.py`) talks **only** to abstract interfaces, never to a concrete engine. Third-party SDKs (`google-genai`, `faster_whisper`, `vosk`, `pvporcupine`, `edge_tts`, `piper`) are imported **only** inside `engines/`. If you find yourself importing an engine SDK anywhere else, stop — you are doing it wrong.

The earlier design had four interfaces; tools require a fifth.

1. **`WakeWordDetector`** — blocks until the wake word is heard.
2. **`STTEngine`** — `transcribe(audio) -> str`. Two implementations (faster-whisper, Vosk).
3. **`LLMProvider`** — the brain. **Must support tool/function calling**, not just single-shot chat (see §4). One implementation now (Gemini).
4. **`TTSEngine`** — `speak(text)`. Two implementations (Edge-TTS, piper).
5. **`ToolRegistry`** — holds the tool definitions and dispatches `execute(name, input) -> result`. New for v1; this is what makes Jarvis *do* things.

Selection happens via a factory in `main.py` that reads config/`.env` and constructs the matching engines, then hands them to `Assistant`.

---

## 4. The agent loop (why tools change the brain)

The earlier chat's brain was single-shot: one user message → one reply. **That is insufficient for tools.** "Summarize that document" is really `read_file` → reason over contents → reply — at least two round trips. So `LLMProvider` must run an **agent loop**:

```
transcript + tool schemas ─► LLM
       ▲                        │
       │             stop_reason == tool_use?
       │                        │  yes
       │             ToolRegistry.execute(name, input)
       │                        │
       └──── append tool_result ┘   (loop)
                                │  no  (final text)
                                ▼
                            reply → TTS
```

Concretely, using Gemini's function-calling API:

1. Send transcript + the tool declarations to Gemini.
2. If Gemini returns a **function call**, execute it via `ToolRegistry`, append the function response to history, and call Gemini again.
3. Repeat until Gemini returns plain text — that is the spoken reply.
4. Cap the loop (e.g. max 5 tool iterations) to prevent runaway calls.

`LLMProvider` owns this loop and depends only on the `ToolRegistry` interface — never on a concrete tool.

---

## 5. Tools — the v1 deliverable

Each tool is a Python function plus a Gemini function-declaration (name, description, JSON-schema parameters). All live under `src/jarvis/tools/`. The registry collects them; the LLM sees only the declarations; the registry executes the functions.

| Tool                 | Parameters                     | Risk     | Guardrail                                  |
|----------------------|--------------------------------|----------|--------------------------------------------|
| `create_folder`      | `path`                         | low      | confine to workspace root                  |
| `write_file`         | `path`, `content`              | medium   | confine to workspace; no silent overwrite  |
| `read_file`          | `path`                         | low      | confine to workspace                       |
| `summarize_document` | `path`                         | low      | wraps `read_file`, then LLM summarizes     |
| `find_file`          | `name`, optional `search_root` | low–med  | scoped roots; cap result count             |

### 5.1 Safety model — the single most important part

An LLM **will** eventually emit a path like `C:\Windows\System32` or one containing `..`. The entire safety of this app rests on one rule:

> **Every path from every tool is resolved and validated against an allowlisted workspace root before any filesystem operation.**

Implement one helper, `_safe_path(user_path) -> Path`, called by **every** tool:

- Resolve to an absolute, symlink-free path (`Path.resolve()`).
- Reject anything that escapes the configured `WORKSPACE_ROOT` (e.g. `C:\Users\<you>\JarvisWorkspace`).
- Reject `..` traversal and absolute paths pointing outside the root.
- Raise a clear error the LLM can read and relay to the user, rather than crashing.

Per-tool rules on top of `_safe_path`:

- **`write_file`** — if the target exists, do **not** overwrite silently; require a confirm flag or a distinct code path. Never destructive by default.
- **`find_file`** — search only within configured, allowlisted roots (default: workspace + a small set of safe user dirs like Documents/Desktop, set in config). Cap results (e.g. 20) so a broad query can't dump the drive.
- **No delete tool in v1.** Deletion, move, and overwrite-in-place are explicitly out of scope until the safety model is proven.

This safety layer is what the earlier chat lacked entirely and is non-negotiable.

---

## 6. Configuration — `.env` vs `config.yaml`

Secrets and machine-specific switches in `.env`; tunables in `config.yaml`. Nothing else in the app reads env/yaml directly — only `config.py`, which loads both into a typed `Settings` object.

### `.env` (gitignored — secrets + provider switches)

```
GEMINI_API_KEY=...
PORCUPINE_ACCESS_KEY=...          # needed at Phase 3

# STT engine switch (you asked for this to be configurable)
STT_PROVIDER=faster_whisper       # faster_whisper | vosk
```

### `config.yaml` (committed — tunables)

```yaml
wake_word:
  keyword: jarvis
  sensitivity: 0.5                 # 0.0–1.0

stt:
  # faster-whisper settings
  whisper_model: base              # tiny | base | small | ...
  # vosk settings
  vosk_model_path: models/vosk-model-small-en-us-0.15
  sample_rate: 16000

llm:
  provider: gemini                 # the switch for swapping providers later
  model: gemini-2.0-flash
  max_tool_iterations: 5
  system_prompt: >
    You are Jarvis, a concise voice assistant. Keep replies short and
    conversational since they are spoken aloud. Avoid lists and markdown.
    When asked to act on files, use the provided tools.

tts:
  provider: edge                   # edge | piper   (configurable)
  edge_voice: en-US-GuyNeural
  piper_model: models/piper/en_US-lessac-medium.onnx

tools:
  workspace_root: C:\Users\CHANGE_ME\JarvisWorkspace
  find_search_roots:
    - C:\Users\CHANGE_ME\Documents
    - C:\Users\CHANGE_ME\Desktop
  find_max_results: 20

conversation:
  silence_timeout_seconds: 8
  sleep_phrases: [go to sleep, goodbye, stop listening]
```

---

## 7. Project structure

```
jarvis/
├── .env                      # secrets + STT switch (gitignored)
├── .env.example              # committed template
├── config.yaml               # settings (committed)
├── requirements.txt
├── README.md
├── models/                   # Vosk / piper models (gitignored)
└── src/jarvis/
    ├── main.py               # factory: builds engines + tools from config, runs Assistant
    ├── assistant.py          # orchestrator + main loop; depends only on interfaces
    ├── config.py             # loads .env + config.yaml into typed Settings
    ├── interfaces/
    │   ├── wake_word.py       # WakeWordDetector ABC
    │   ├── stt.py             # STTEngine ABC
    │   ├── llm.py             # LLMProvider ABC (+ Message type) — includes tool loop
    │   ├── tts.py             # TTSEngine ABC
    │   └── tools.py           # ToolRegistry ABC + Tool/ToolResult types
    ├── engines/              # ONLY place third-party SDKs are imported
    │   ├── porcupine_wake.py
    │   ├── whisper_stt.py     # faster-whisper
    │   ├── vosk_stt.py        # Vosk
    │   ├── gemini_llm.py      # brain + Gemini function calling
    │   ├── edge_tts.py
    │   └── piper_tts.py
    └── tools/                # the v1 deliverable
        ├── registry.py        # collects declarations, dispatches execute()
        ├── safe_path.py       # _safe_path() — the allowlist guard
        ├── create_folder.py
        ├── write_file.py
        ├── read_file.py
        ├── summarize_document.py
        └── find_file.py
```

---

## 8. Build phases

Build top to bottom. Each phase ends with something runnable and testable on its own. Do not pull a later phase's work forward.

Note the reordering vs the earlier chat: **tools come right after the brain, before audio.** Tools are the priority and the riskiest logic, so they get built and tested in a plain text REPL — no microphone required — before any audio complexity is layered on.

- **Phase 0 — Skeleton + brain (text only).** Config loader, all five interfaces, `GeminiProvider` (single-shot first), the audio engines stubbed. Main loop reads typed input, prints replies. Proves config + Gemini + history + loop.
  *Test:* type a multi-turn conversation; context carries.

- **Phase 1 — Tools + agent loop (still text only).** Build `safe_path.py` and the `ToolRegistry`. Implement all five tools. Upgrade `GeminiProvider` to the tool-calling loop (§4). Wire tools through the registry.
  *Test (in the REPL, no mic):* "create a folder called notes", "write a file test.txt saying hello", "summarize <doc>", "find file report.docx". Confirm `_safe_path` rejects `..` and paths outside the workspace.

- **Phase 2 — Voice out.** Implement both `EdgeTTS` and `PiperTTS`; select via `tts.provider`. Replies are spoken.
  *Test:* type, hear Jarvis speak, on both providers.

- **Phase 3 — Voice in.** Implement both `WhisperSTT` and `VoskSTT`; select via `STT_PROVIDER`. Replace typed input with spoken input.
  *Test:* speak, get spoken replies, on both STT engines.

- **Phase 4 — Wake word.** Implement `PorcupineWake`. App idles until "Jarvis", greets, runs the conversation+tools loop, returns to idle on silence or a sleep phrase. This is complete Jarvis.
  *Test:* the full experience end to end, including a spoken tool command like "Jarvis… create a folder called demo."

---

## 9. Rules for the build (conventions)

1. **Interfaces only in the orchestrator.** `assistant.py` never imports a concrete engine or tool.
2. **SDKs only in `engines/`.** Never import `google-genai`, `faster_whisper`, `vosk`, `pvporcupine`, `edge_tts`, or `piper` outside `engines/`.
3. **Provider-abstracted brain.** Gemini is the only LLM wired now; others are drop-in `LLMProvider`s later. Selection is one config line.
4. **Phased and runnable.** Each phase runs and is testable before the next.
5. **Secrets in `.env`, settings in `config.yaml`.** Never hardcode a key; never commit `.env`.
6. **Windows-first.** `pathlib` everywhere; no hardcoded `/`.
7. **Every tool path goes through `_safe_path`.** No exceptions. No tool touches the filesystem without it.
8. **No destructive tools in v1.** No delete/move/overwrite-in-place until the safety model is proven.
9. **Stay in scope.** See §10.

---

## 10. Out of scope for v1 (do not build unprompted)

- Delete / move / rename tools
- Clap-to-wake (Porcupine handles the wake word)
- Persisted / cross-session memory
- Multiple LLM providers actually wired (interface ready; only Gemini built)
- GUI / system tray / autostart
- Barge-in (interrupting Jarvis mid-sentence)
- Anything that writes outside the workspace root

---

## 11. requirements.txt (target)

```
# Brain + tools
google-genai

# Config
python-dotenv
pyyaml

# STT (choose at runtime via STT_PROVIDER)
faster-whisper
vosk
sounddevice

# TTS (choose via tts.provider)
edge-tts
piper-tts

# Wake word (Phase 4)
pvporcupine

# Tooling
ruff
```

---

## 12. How to hand this to Fable

Point Fable at this file and build **phase by phase**, stopping for a test after each. A good opening instruction:

> Build **Phase 0** exactly as specified in JARVIS.md §8: the package layout in §7, all five interfaces in §3, a single-shot `GeminiProvider`, stubbed audio engines, and a typed-input REPL loop. Follow the rules in §9. Stop when I can hold a multi-turn typed conversation, so I can test before Phase 1.

Then, for the phase that matters most:

> Build **Phase 1**: `safe_path.py` per §5.1, the `ToolRegistry`, all five tools from §5, and upgrade `GeminiProvider` to the tool-calling agent loop in §4. Keep it text-only so I can test tools in the REPL before adding audio.
