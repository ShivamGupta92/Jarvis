"""read_file — read a text file's contents from inside the workspace."""

from __future__ import annotations

from pathlib import Path

from ..config import ToolsSettings
from ..interfaces import Tool, ToolResult
from .safe_path import SafePathError, _safe_path

MAX_CHARS = 50_000  # protect the context window from huge files


def read_text_safely(path: str, root: Path, max_chars: int = MAX_CHARS) -> str:
    """Shared guarded read used by read_file and summarize_document.
    Raises SafePathError / OSError for the registry to translate."""
    target = _safe_path(path, root)
    if not target.exists():
        raise SafePathError(f"No file found at {target}.")
    if target.is_dir():
        raise SafePathError(f"{target} is a folder, not a file.")
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except UnicodeDecodeError as exc:  # errors="replace" makes this unlikely
        raise SafePathError(f"{target} is not a readable text file: {exc}") from exc
    if len(text) > max_chars:
        return text[:max_chars] + f"\n\n[...truncated at {max_chars} characters]"
    return text


def build(settings: ToolsSettings) -> Tool:
    root = settings.workspace_root

    def run(path: str) -> ToolResult:
        text = read_text_safely(path, root)
        return ToolResult(True, output=text)

    return Tool(
        name="read_file",
        description=(
            "Read the contents of a text file inside the Jarvis workspace "
            "and return them. Paths are relative to the workspace root."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to the workspace root, e.g. 'notes/todo.txt'.",
                }
            },
            "required": ["path"],
        },
        run=run,
    )
