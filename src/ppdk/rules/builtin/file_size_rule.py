# ====== Code Summary ======
# Built-in rule ppdk.file_size: refuses changed files above a size, so that archives, datasets and
# build output stay out of git.

# ====== Standard Library Imports ======
from __future__ import annotations

from typing import ClassVar, Final

# ====== Local Project Imports ======
from ..rule import RuleConfigError, Rule
from ..rule_types import Finding, RuleContext, RuleResult

# ====== Constants ======
_DEFAULT_MAX_KB: Final[int] = 1024


class FileSizeRule(Rule):
    """Refuses a changed file larger than `max_kb` kilobytes.

    Options:
        max_kb (int): The largest size allowed, in kilobytes (default: 1024).
    """

    OPTIONS: ClassVar[frozenset[str]] = frozenset({"max_kb"})

    # Private attributes
    _max_bytes: int

    # =======================
    #   Private Methods
    # =======================
    def _configure(self) -> None:
        """Read the size limit."""
        max_kb = self._option("max_kb", int, _DEFAULT_MAX_KB)
        if max_kb <= 0:
            raise RuleConfigError(f"{self.name}: option 'max_kb' must be positive")
        self._max_bytes = max_kb * 1024

    # =======================
    #   Public Methods
    # =======================
    def run(self, context: RuleContext) -> RuleResult:
        """Refuse every changed file over the limit.

        Args:
            context (RuleContext): The changed files and their reader.

        Returns:
            RuleResult: One finding per file over the limit.
        """
        findings: list[Finding] = []
        for path in context.changed_files:
            content = context.reader.read_bytes(path)
            if content is not None and len(content) > self._max_bytes:
                findings.append(
                    Finding(
                        message=(
                            f"file of {len(content) // 1024} KB, over {self._max_bytes // 1024} "
                            "KB: keep large files out of git (storage, release asset, .gitignore)"
                        ),
                        path=path,
                    )
                )
        return RuleResult(findings=tuple(findings))
