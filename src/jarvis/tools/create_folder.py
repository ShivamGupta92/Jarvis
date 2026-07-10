"""create_folder — make a directory inside the workspace."""

from __future__ import annotations

from ..config import ToolsSettings
from ..interfaces import Tool, ToolResult
from .safe_path import _safe_path


def build(settings: ToolsSettings) -> Tool:
    root = settings.workspace_root

    def run(path: str) -> ToolResult:
        target = _safe_path(path, root)
        if target.is_dir():
            return ToolResult(True, output=f"Folder already exists: {target}")
        if target.exists():
            return ToolResult(False, error=f"A file already exists at {target}; not a folder.")
        target.mkdir(parents=True)
        return ToolResult(True, output=f"Created folder: {target}")

    return Tool(
        name="create_folder",
        description=(
            "Create a folder (directory) inside the Jarvis workspace. "
            "Parent folders are created as needed. Paths are relative to "
            "the workspace root."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Folder path relative to the workspace root, e.g. 'notes' or 'projects/todo'.",
                }
            },
            "required": ["path"],
        },
        run=run,
    )
