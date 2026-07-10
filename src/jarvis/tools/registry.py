"""Concrete ToolRegistry: collects declarations, dispatches execute().

execute() never raises — every failure (unknown tool, bad arguments,
guard rejection, OS error) becomes an unsuccessful ToolResult whose
message the LLM can read and relay to the user.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..interfaces import Tool, ToolRegistry, ToolResult
from .safe_path import SafePathError


class Registry(ToolRegistry):
    def __init__(self, tools: Iterable[Tool]) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(f"Duplicate tool name: {tool.name}")
            self._tools[tool.name] = tool

    def declarations(self) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(False, error=f"Unknown tool '{name}'.")
        try:
            return tool.run(**arguments)
        except SafePathError as exc:
            return ToolResult(False, error=str(exc))
        except TypeError as exc:
            return ToolResult(False, error=f"Bad arguments for {name}: {exc}")
        except OSError as exc:
            return ToolResult(False, error=f"Filesystem error in {name}: {exc}")
        except Exception as exc:  # never let a tool crash the agent loop
            return ToolResult(False, error=f"{name} failed: {type(exc).__name__}: {exc}")
