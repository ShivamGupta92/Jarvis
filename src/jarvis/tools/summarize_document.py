"""summarize_document — wraps the guarded read; the LLM does the actual
summarizing on the next agent-loop iteration, so this tool just returns
the document text with summarizing instructions.
"""

from __future__ import annotations

from ..config import ToolsSettings
from ..interfaces import Tool, ToolResult
from .read_file import read_text_safely

MAX_CHARS = 20_000  # tighter than read_file: this text exists only to be summarized


def build(settings: ToolsSettings) -> Tool:
    root = settings.workspace_root

    def run(path: str) -> ToolResult:
        text = read_text_safely(path, root, max_chars=MAX_CHARS)
        return ToolResult(
            True,
            output=(
                "Document contents follow. Summarize them concisely for the "
                f"user in a spoken reply.\n\n{text}"
            ),
        )

    return Tool(
        name="summarize_document",
        description=(
            "Fetch a document from the Jarvis workspace so you can summarize "
            "it. Returns the document text; reply to the user with a short "
            "spoken summary of it."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Document path relative to the workspace root, e.g. 'reports/q3.txt'.",
                }
            },
            "required": ["path"],
        },
        run=run,
    )
