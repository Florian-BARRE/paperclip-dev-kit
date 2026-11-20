# ====== Code Summary ======
# Built-in rule ppdk.secret: refuses lines that look like a credential (private keys, provider
# tokens), plus the extra patterns a repository adds.

# ====== Standard Library Imports ======
from __future__ import annotations

import re
from typing import ClassVar, Final

# ====== Local Project Imports ======
from ..rule import RuleConfigError
from .file_content_rule import FileContentRule

# ====== Constants ======
# Formats with a recognisable prefix only: a generic "password = ..." test would refuse too much.
_KNOWN_SECRETS: Final[dict[str, str]] = {
    "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
    "GitHub token": r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{60,}\b",
    "Anthropic key": r"\bsk-ant-[A-Za-z0-9_-]{20,}",
    "OpenAI key": r"\bsk-(proj-)?[A-Za-z0-9]{32,}",
    "Slack token": r"\bxox[abpors]-[A-Za-z0-9-]{10,}",
}


class SecretRule(FileContentRule):
    """Refuses a line matching a known credential format.

    Options:
        patterns (list[str]): Extra regular expressions refused in this repository.
    """

    OPTIONS: ClassVar[frozenset[str]] = frozenset({"patterns"})

    # Private attributes
    _patterns: dict[str, re.Pattern[str]]

    # =======================
    #   Private Methods
    # =======================
    def _configure(self) -> None:
        """Compile the known formats and the repository's extra patterns."""
        self._patterns = {label: re.compile(regex) for label, regex in _KNOWN_SECRETS.items()}
        for regex in self._string_list_option("patterns", []):
            try:
                self._patterns[f"pattern {regex!r}"] = re.compile(regex)
            except re.error as error:
                raise RuleConfigError(f"{self.name}: invalid pattern {regex!r}: {error}") from None

    def _check_line(self, line: str) -> str | None:
        """Return a reason when `line` matches a secret format."""
        for label, pattern in self._patterns.items():
            if pattern.search(line):
                return (
                    f"looks like a secret ({label}): remove it, keep it outside git "
                    "(an untracked .env), and rotate it if it was ever pushed"
                )
        return None
