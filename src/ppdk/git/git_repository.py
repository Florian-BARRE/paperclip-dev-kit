# ====== Code Summary ======
# The kit's only access to git: the repository root, the current branch, the files a commit or a
# push changes, and the content of a file in a given version.

# ====== Standard Library Imports ======
from __future__ import annotations

import subprocess
from pathlib import Path

# ====== Third-Party Library Imports ======
from loggerplusplus import LoggerClass


class GitError(RuntimeError):
    """A git command failed: not a repository, unknown revision..."""


class GitRepository(LoggerClass):
    """Runs read-only git commands in one repository.

    Args:
        root (Path): The repository root (the top of the work tree).
    """

    # Public attributes
    root: Path

    def __init__(self, root: Path) -> None:
        LoggerClass.__init__(self)
        self.root = root

    # =======================
    #   Private Methods
    # =======================
    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        """Run `git <args>` in the repository and return the completed process.

        Raises:
            GitError: If `check` is set and git exits non-zero.
        """
        # core.quotepath=false: paths with accents come out as text, not as octal escapes.
        completed = subprocess.run(
            ["git", "-c", "core.quotepath=false", *args],
            cwd=self.root,
            capture_output=True,
            check=False,
        )
        if check and completed.returncode != 0:
            message = completed.stderr.decode("utf-8", "replace").strip()
            raise GitError(f"git {' '.join(args)}: {message}")
        return completed

    def _lines(self, *args: str) -> tuple[str, ...]:
        """Run git and return its non-empty output lines."""
        output = self._run(*args).stdout.decode("utf-8", "replace")
        return tuple(line for line in output.splitlines() if line)

    def _has_revision(self, revision: str) -> bool:
        """Tell whether `revision` names a commit."""
        completed = self._run(
            "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}", check=False
        )
        return completed.returncode == 0

    # =======================
    #   Public Methods
    # =======================
    @classmethod
    def discover(cls, start: Path) -> GitRepository:
        """Return the repository that contains `start`.

        Raises:
            GitError: If `start` is not inside a git work tree.
        """
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=start, capture_output=True, check=False
        )
        if completed.returncode != 0:
            raise GitError(f"{start} is not inside a git repository")
        return cls(Path(completed.stdout.decode().strip()))

    def current_branch(self) -> str | None:
        """Return the checked-out branch, or None when HEAD is detached (a CI checkout)."""
        completed = self._run("symbolic-ref", "--short", "-q", "HEAD", check=False)
        name = completed.stdout.decode().strip()
        return name or None

    def staged_files(self) -> tuple[str, ...]:
        """Return the files added, copied, modified or renamed in the index."""
        return self._lines("diff", "--cached", "--name-only", "--diff-filter=ACMR")

    def base_revision(self, base: str) -> str | None:
        """Return the revision a branch is compared with: `origin/<base>`, `<base>` or None."""
        for candidate in (f"origin/{base}", base):
            if self._has_revision(candidate):
                return candidate
        return None

    def changed_files_since(self, base_revision: str | None) -> tuple[str, ...]:
        """Return the files added or modified between the merge base with `base_revision` and HEAD.

        Without a base (a repository with no base branch yet), every tracked file counts.
        """
        if base_revision is None or not self._has_revision("HEAD"):
            return self._lines("ls-files")
        merge_base = self._run("merge-base", base_revision, "HEAD", check=False)
        if merge_base.returncode != 0:
            return self._lines("ls-files")
        start = merge_base.stdout.decode().strip()
        return self._lines("diff", "--name-only", "--diff-filter=ACMR", f"{start}..HEAD")

    def read_staged(self, path: str) -> bytes | None:
        """Return the content of `path` in the index, or None if it is not there."""
        completed = self._run("show", f":{path}", check=False)
        return completed.stdout if completed.returncode == 0 else None

    def read_revision(self, revision: str, path: str) -> bytes | None:
        """Return the content of `path` at `revision`, or None if it does not exist there."""
        completed = self._run("show", f"{revision}:{path}", check=False)
        return completed.stdout if completed.returncode == 0 else None
