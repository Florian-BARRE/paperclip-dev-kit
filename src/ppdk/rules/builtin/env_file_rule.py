# ====== Code Summary ======
# Built-in rule ppdk.env_file: a real .env file never enters git; only the example files the
# repository allows (.env.example by default) may be committed.

# ====== Standard Library Imports ======
from __future__ import annotations

from pathlib import PurePosixPath
from typing import ClassVar

# ====== Local Project Imports ======
from ..rule import Rule
from ..rule_types import Finding, RuleContext, RuleResult


class EnvFileRule(Rule):
    """Refuses `.env` and `.env.*` files, except the allowed example names.

    Options:
        allow (list[str]): File names that may be committed (default: `.env.example`).
    """

    OPTIONS: ClassVar[frozenset[str]] = frozenset({"allow"})

    # Private attributes
    _allowed: frozenset[str]

    # =======================
    #   Private Methods
    # =======================
    def _configure(self) -> None:
        """Read the allowed file names."""
        self._allowed = frozenset(self._string_list_option("allow", [".env.example"]))

    def _is_env_file(self, path: str) -> bool:
        """Tell whether `path` names an environment file that is not allowed."""
        name = PurePosixPath(path).name
        return (name == ".env" or name.startswith(".env.")) and name not in self._allowed

    # =======================
    #   Public Methods
    # =======================
    def run(self, context: RuleContext) -> RuleResult:
        """Refuse every added or modified environment file.

        Args:
            context (RuleContext): The changed files.

        Returns:
            RuleResult: One finding per environment file.
        """
        findings = [
            Finding(
                message=(
                    "environment file in git: unstage it (git rm --cached), add it to "
                    ".gitignore and describe its variables in .env.example"
                ),
                path=path,
            )
            for path in context.changed_files
            if self._is_env_file(path) and context.reader.read_bytes(path) is not None
        ]
        return RuleResult(findings=tuple(findings))
