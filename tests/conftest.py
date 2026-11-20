# ====== Code Summary ======
# Shared test fixtures: a throw-away git repository with a .ppdk/ folder, and an in-memory file
# reader to test rules without git.

# ====== Standard Library Imports ======
from __future__ import annotations

import io
import subprocess
from pathlib import Path

# ====== Third-Party Library Imports ======
import pytest

# ====== Internal Project Imports ======
from ppdk import FileReader, RuleContext, Stage
from ppdk.application import ExitCode, PpdkApplication
from ppdk.rules.builtin import BUILTIN_RULES


class MemoryReader(FileReader):
    """A FileReader over a dict of path -> bytes."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self._files = files

    def read_bytes(self, path: str) -> bytes | None:
        """Return the stored content, or None."""
        return self._files.get(path)


def make_context(
    files: dict[str, bytes], *, stage: Stage = Stage.COMMIT, branch: str = "feature"
) -> RuleContext:
    """Build a RuleContext whose changed files are `files`."""
    return RuleContext(
        stage=stage,
        repo_root=Path.cwd(),
        base_branch="main",
        branch=branch,
        changed_files=tuple(files),
        reader=MemoryReader(files),
        default_timeout=60,
    )


class GitSandbox:
    """A temporary git repository with helpers to write, stage, commit and run ppdk."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "test")
        self.write("README.md", "readme\n")
        self.commit("init")

    def _git(self, *args: str) -> str:
        """Run git in the sandbox and return its output."""
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True, text=True
        ).stdout

    def write(self, path: str, content: str) -> None:
        """Write a file in the work tree."""
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def config(self, toml: str) -> None:
        """Write .ppdk/project.toml."""
        self.write(".ppdk/project.toml", toml)

    def stage(self, *paths: str) -> None:
        """Stage files (everything when no path is given)."""
        self._git("add", *(paths or ("-A",)))

    def commit(self, message: str) -> None:
        """Stage everything and commit."""
        self._git("add", "-A")
        self._git("commit", "-q", "--no-verify", "-m", message)

    def switch(self, branch: str) -> None:
        """Create and check out a branch."""
        self._git("switch", "-q", "-c", branch)

    def run(self, method: str, *args: object) -> tuple[ExitCode, str]:
        """Call a PpdkApplication method and return its exit code and report."""
        out = io.StringIO()
        app = PpdkApplication(cwd=self.root, builtin_rules=BUILTIN_RULES, out=out)
        code = getattr(app, method)(*args)
        return code, out.getvalue()


@pytest.fixture
def sandbox(tmp_path: Path) -> GitSandbox:
    """A fresh git repository on branch main with one commit."""
    return GitSandbox(tmp_path)
