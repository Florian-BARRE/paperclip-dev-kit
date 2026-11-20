# ====== Code Summary ======
# The values a rule works with: the stage it runs at, what it reports (findings, result) and the
# context the kit hands it (changed files, branch, a reader for the files' content).

# ====== Standard Library Imports ======
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Stage(str, Enum):
    """The moments the kit runs rules at."""

    COMMIT = "commit"
    PUSH = "push"
    CI = "ci"


class Severity(str, Enum):
    """What a failing rule does: refuse the commit or push, or only warn."""

    ERROR = "error"
    WARN = "warn"


@dataclass(frozen=True)
class Finding:
    """One problem found by a rule, located when possible.

    Args:
        message (str): What is wrong and, ideally, how to fix it.
        path (str | None): Repository-relative file the problem is in.
        line (int | None): 1-based line number in that file.
    """

    message: str
    path: str | None = None
    line: int | None = None

    def location(self) -> str:
        """Return `path:line`, `path` or an empty string, for the report."""
        if self.path is None:
            return ""
        return f"{self.path}:{self.line}" if self.line is not None else self.path


@dataclass(frozen=True)
class RuleResult:
    """What a rule's `run` returns: no finding means the rule passed.

    Args:
        findings (tuple[Finding, ...]): The problems found, empty when the rule passed.
    """

    findings: tuple[Finding, ...] = ()

    @property
    def passed(self) -> bool:
        """True when the rule found nothing."""
        return not self.findings

    @classmethod
    def ok(cls) -> RuleResult:
        """Build a passing result."""
        return cls()

    @classmethod
    def fail(cls, *findings: Finding) -> RuleResult:
        """Build a failing result from one or more findings.

        Raises:
            ValueError: If no finding is given (a failure must say why).
        """
        if not findings:
            raise ValueError("RuleResult.fail needs at least one Finding")
        return cls(findings=tuple(findings))


class FileReader(ABC):
    """Reads a file in the version being checked (staged at commit, pushed afterwards)."""

    @abstractmethod
    def read_bytes(self, path: str) -> bytes | None:
        """Return the file's content, or None if the file does not exist in that version.

        Args:
            path (str): Repository-relative path.
        """

    def read_text(self, path: str) -> str | None:
        """Return the file's content as UTF-8 text, or None if it is missing or binary.

        Args:
            path (str): Repository-relative path.
        """
        content = self.read_bytes(path)
        if content is None or b"\0" in content:
            return None
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return None


@dataclass(frozen=True)
class PushedRef:
    """One ref a `git push` sends, as git gives it to the pre-push hook.

    Args:
        local_ref (str): The local ref pushed (`refs/heads/feature`).
        remote_ref (str): The remote ref it updates (`refs/heads/main`).
    """

    local_ref: str
    remote_ref: str


@dataclass(frozen=True)
class RuleContext:
    """Everything a rule may look at. Built by the kit for each rule, never by the rule itself.

    Args:
        stage (Stage): The moment the rule runs at.
        repo_root (Path): Absolute path of the repository.
        base_branch (str): The branch work merges into (`[project] base`).
        branch (str | None): The current branch, None when HEAD is detached.
        changed_files (tuple[str, ...]): Files added or modified by the change being checked,
            already narrowed to the rule's `paths` when it has some.
        reader (FileReader): Reads those files in the version being checked.
        default_timeout (int): Seconds a long check (a command) may take, from `[project] timeout`.
        pushed_refs (tuple[PushedRef, ...]): The refs being pushed (push stage only).
    """

    stage: Stage
    repo_root: Path
    base_branch: str
    branch: str | None
    changed_files: tuple[str, ...]
    reader: FileReader
    default_timeout: int
    pushed_refs: tuple[PushedRef, ...] = field(default_factory=tuple)

    def read_text(self, path: str) -> str | None:
        """Return a file's text in the version being checked (see `FileReader.read_text`)."""
        return self.reader.read_text(path)
