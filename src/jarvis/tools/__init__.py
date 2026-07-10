"""The v1 tool set. Every tool resolves every path through _safe_path
before touching the filesystem — no exceptions.
"""

from ..config import ToolsSettings
from ..interfaces import Tool
from . import create_folder, find_file, read_file, summarize_document, write_file
from .registry import Registry


def build_registry(settings: ToolsSettings) -> Registry:
    """Construct all five v1 tools bound to the configured workspace."""
    settings.workspace_root.expanduser().mkdir(parents=True, exist_ok=True)
    tools: list[Tool] = [
        create_folder.build(settings),
        write_file.build(settings),
        read_file.build(settings),
        summarize_document.build(settings),
        find_file.build(settings),
    ]
    return Registry(tools)
