# ====== Code Summary ======
# The two ways rules read a changed file: from the index at commit time (what is really committed,
# not the work tree), and from a revision at push and CI time.

# ====== Standard Library Imports ======
from __future__ import annotations

# ====== Internal Project Imports ======
from ppdk.rules.rule_types import FileReader

# ====== Local Project Imports ======
from .git_repository import GitRepository


class StagedFileReader(FileReader):
    """Reads files as they are staged for the commit being made.

    Args:
        git (GitRepository): The repository.
    """

    # Private attributes
    _git: GitRepository

    def __init__(self, git: GitRepository) -> None:
        self._git = git

    def read_bytes(self, path: str) -> bytes | None:
        """Return the staged content of `path`, or None if it is not staged."""
        return self._git.read_staged(path)


class RevisionFileReader(FileReader):
    """Reads files as they are in one revision (HEAD, the commit being pushed or tested).

    Args:
        git (GitRepository): The repository.
        revision (str): The revision to read from.
    """

    # Private attributes
    _git: GitRepository
    _revision: str

    def __init__(self, git: GitRepository, revision: str) -> None:
        self._git = git
        self._revision = revision

    def read_bytes(self, path: str) -> bytes | None:
        """Return the content of `path` at the revision, or None if it does not exist there."""
        return self._git.read_revision(self._revision, path)
