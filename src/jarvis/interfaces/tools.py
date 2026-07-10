"""ToolRegistry ABC + Tool/ToolResult types.

Tools are plain Python functions plus a provider-agnostic declaration
(name, description, JSON-schema parameters). The LLM sees only the
declarations; the registry executes the functions. LLM providers depend
on the ToolRegistry interface — never on a concrete tool.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    """Outcome of one tool execution, fed back to the LLM as text."""

    success: bool
    output: str = ""
    error: str = ""

    def for_llm(self) -> dict[str, Any]:
        """Shape sent back to the model as the function response."""
        if self.success:
            return {"output": self.output}
        return {"error": self.error}


@dataclass(frozen=True)
class Tool:
    """A callable tool plus its declaration for the LLM."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema (lowercase standard types)
    run: Callable[..., ToolResult] = field(repr=False)


class ToolRegistry(ABC):
    """Holds tool declarations and dispatches execution by name."""

    @abstractmethod
    def declarations(self) -> list[dict[str, Any]]:
        """Provider-agnostic declarations:
        [{"name": ..., "description": ..., "parameters": <JSON schema>}, ...]
        """
        raise NotImplementedError

    @abstractmethod
    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Run the named tool. Must never raise — all failures come back
        as an unsuccessful ToolResult the LLM can read and relay.
        """
        raise NotImplementedError
