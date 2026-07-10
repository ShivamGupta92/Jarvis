"""write_file — write a document inside the workspace. Never overwrites
silently: an existing target requires the explicit overwrite flag, which
the model should only set after the user confirms.
"""

from __future__ import annotations

from ..config import ToolsSettings
from ..interfaces import Tool, ToolResult
from .safe_path import _safe_path


def build(settings: ToolsSettings) -> Tool:
    root = settings.workspace_root

    def run(path: str, content: str, overwrite: bool = False) -> ToolResult:
        target = _safe_path(path, root)
        if target.is_dir():
            return ToolResult(False, error=f"{target} is a folder, not a file.")
        if target.exists() and not overwrite:
            return ToolResult(
                False,
                error=(
                    f"File already exists: {target}. Nothing was written. "
                    "Ask the user to confirm overwriting; only if they agree, "
                    "call write_file again with overwrite=true."
                ),
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(True, output=f"Wrote {len(content)} characters to {target}")

    return Tool(
        name="write_file",
        description=(
            "Write a text file inside the Jarvis workspace. If the file "
            "already exists the call fails unless overwrite=true, which you "
            "must only set after the user has explicitly confirmed."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to the workspace root, e.g. 'notes/todo.txt'.",
                },
                "content": {
                    "type": "string",
                    "description": "The full text content to write.",
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Set true ONLY after the user explicitly confirmed replacing an existing file. Defaults to false.",
                },
            },
            "required": ["path", "content"],
        },
        run=run,
    )
