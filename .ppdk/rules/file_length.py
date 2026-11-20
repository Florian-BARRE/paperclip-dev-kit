# ====== Code Summary ======
# The kit's own structure rule (coding standards): every Python module of src/ starts with its Code
# Summary header (packages' __init__.py excepted) and stays under 400 lines.

# ====== Standard Library Imports ======
from __future__ import annotations

from pathlib import PurePosixPath
from typing import ClassVar, Final

# ====== Third-Party Library Imports ======
from ppdk import Finding, Rule, RuleContext, RuleResult

# ====== Constants ======
_HEADER: Final[str] = "# ====== Code Summary ======"


class FileLengthRule(Rule):
    """Refuses a src/ module over `max_lines` lines or without its Code Summary header.

    Options:
        max_lines (int): The longest module allowed (default: 400).
    """

    OPTIONS: ClassVar[frozenset[str]] = frozenset({"max_lines"})

    # Private attributes
    _max_lines: int

    def _configure(self) -> None:
        """Read the line limit."""
        self._max_lines = self._option("max_lines", int, 400)

    def _check(self, path: str, text: str) -> list[Finding]:
        """Return the findings of one module."""
        findings: list[Finding] = []
        lines = text.splitlines()
        if len(lines) > self._max_lines:
            findings.append(
                Finding(f"{len(lines)} lines, over {self._max_lines}: split the module", path)
            )
        if PurePosixPath(path).name != "__init__.py" and (not lines or lines[0] != _HEADER):
            findings.append(Finding(f"first line must be '{_HEADER}'", path, 1))
        return findings

    def run(self, context: RuleContext) -> RuleResult:
        """Check every changed Python module."""
        findings: list[Finding] = []
        for path in context.changed_files:
            text = context.read_text(path)
            if path.endswith(".py") and text is not None:
                findings.extend(self._check(path, text))
        return RuleResult(findings=tuple(findings))
