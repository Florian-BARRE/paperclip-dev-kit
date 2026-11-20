# ====== Code Summary ======
# Base of the built-in rules that read every changed text file line by line (conflict markers,
# secrets): the loop over files lives here once, each rule only says what a bad line is.

# ====== Standard Library Imports ======
from __future__ import annotations

from abc import abstractmethod

# ====== Local Project Imports ======
from ..rule import Rule
from ..rule_types import Finding, RuleContext, RuleResult


class FileContentRule(Rule):
    """A rule that inspects each changed text file; binary and deleted files are skipped."""

    # =======================
    #   Private Methods
    # =======================
    @abstractmethod
    def _check_line(self, line: str) -> str | None:
        """Return why `line` is refused, or None when it is fine.

        Args:
            line (str): One line of a changed file, without its line ending.
        """

    # =======================
    #   Public Methods
    # =======================
    def run(self, context: RuleContext) -> RuleResult:
        """Check every line of every changed text file.

        Args:
            context (RuleContext): The changed files and their reader.

        Returns:
            RuleResult: One finding per refused line.
        """
        findings: list[Finding] = []
        for path in context.changed_files:
            text = context.read_text(path)
            if text is None:
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                reason = self._check_line(line)
                if reason is not None:
                    findings.append(Finding(message=reason, path=path, line=number))
        return RuleResult(findings=tuple(findings))
