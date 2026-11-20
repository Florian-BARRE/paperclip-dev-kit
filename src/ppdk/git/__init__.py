"""Read-only access to the repository being checked."""

from .file_readers import RevisionFileReader, StagedFileReader
from .git_repository import GitError, GitRepository

__all__ = ["GitError", "GitRepository", "RevisionFileReader", "StagedFileReader"]
