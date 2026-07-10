"""_safe_path — the allowlist guard every tool must call.

The single rule the app's safety rests on: every path from every tool is
resolved and validated against the allowlisted workspace root before any
filesystem operation. An LLM will eventually emit 'C:\\Windows\\System32'
or a path containing '..'; this is what stops it.
"""

from __future__ import annotations

from pathlib import Path


class SafePathError(Exception):
    """Raised for any path outside the allowlist. The message is written
    for the LLM to read and relay to the user — never a crash."""


def _safe_path(user_path: str, root: Path) -> Path:
    """Resolve user_path against root and return the absolute, symlink-free
    result, or raise SafePathError if it escapes root.

    Relative paths are taken relative to root. Absolute paths are allowed
    only if they resolve to somewhere inside root. '..' traversal is
    neutralized by Path.resolve() and then caught by the containment check.
    """
    text = str(user_path).strip()
    if not text:
        raise SafePathError("Empty path. Provide a file or folder path inside the workspace.")

    root_resolved = root.expanduser().resolve()
    raw = Path(text).expanduser()
    candidate = raw if raw.is_absolute() else root_resolved / raw
    resolved = candidate.resolve()

    if not resolved.is_relative_to(root_resolved):
        raise SafePathError(
            f"Path '{user_path}' is outside the Jarvis workspace ({root_resolved}). "
            "Only paths inside the workspace are allowed."
        )
    return resolved


def _safe_path_in_roots(user_path: str, roots: tuple[Path, ...]) -> Path:
    """Like _safe_path but for read-only operations allowed in any of several
    allowlisted roots (used by find_file's search_root)."""
    last_error: SafePathError | None = None
    for root in roots:
        try:
            return _safe_path(user_path, root)
        except SafePathError as exc:
            last_error = exc
    allowed = ", ".join(str(r.expanduser().resolve()) for r in roots)
    raise SafePathError(
        f"Path '{user_path}' is not inside any allowed search root. Allowed roots: {allowed}."
    ) from last_error
