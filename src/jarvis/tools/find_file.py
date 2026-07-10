"""find_file — locate a file by name, only within allowlisted roots
(workspace + the configured safe user dirs), with a result cap so a broad
query can't dump the drive.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..config import ToolsSettings
from ..interfaces import Tool, ToolResult
from .safe_path import _safe_path_in_roots


def _walk_matches(root: Path, needle: str, limit: int) -> tuple[list[Path], bool]:
    """Case-insensitive substring match on file names under root.
    Unreadable directories are skipped, never fatal. Returns (matches,
    hit_limit)."""
    matches: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(root, onerror=lambda _e: None):
        for filename in filenames:
            if needle in filename.lower():
                matches.append(Path(dirpath) / filename)
                if len(matches) >= limit:
                    return matches, True
    return matches, False


def build(settings: ToolsSettings) -> Tool:
    allowed_roots = (settings.workspace_root, *settings.find_search_roots)
    max_results = settings.find_max_results

    def run(name: str, search_root: str = "") -> ToolResult:
        needle = name.strip().lower()
        if not needle:
            return ToolResult(False, error="Provide a file name (or part of one) to search for.")

        if search_root.strip():
            roots = [_safe_path_in_roots(search_root, allowed_roots)]
        else:
            roots = [r.expanduser().resolve() for r in allowed_roots]

        matches: list[Path] = []
        hit_limit = False
        for root in roots:
            if not root.is_dir():
                continue
            found, hit_limit = _walk_matches(root, needle, max_results - len(matches))
            matches.extend(found)
            if hit_limit:
                break

        if not matches:
            searched = ", ".join(str(r) for r in roots)
            return ToolResult(True, output=f"No files matching '{name}' found in: {searched}.")
        listing = "\n".join(str(p) for p in matches)
        note = f" (stopped at the first {max_results} matches)" if hit_limit else ""
        return ToolResult(True, output=f"Found {len(matches)} file(s){note}:\n{listing}")

    return Tool(
        name="find_file",
        description=(
            "Locate files by name on the PC. Searches the Jarvis workspace "
            "and a small set of allowed user folders (e.g. Documents, "
            "Desktop). Matches are case-insensitive substring matches on "
            "the file name."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The file name, or part of it, e.g. 'report.docx' or 'report'.",
                },
                "search_root": {
                    "type": "string",
                    "description": "Optional folder to search in instead of all allowed roots. Must be inside an allowed root.",
                },
            },
            "required": ["name"],
        },
        run=run,
    )
