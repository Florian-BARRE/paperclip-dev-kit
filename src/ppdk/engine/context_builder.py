# ====== Code Summary ======
# Builds the RuleContext of a stage from git: at commit the staged files read from the index, at
# push and in CI the files the branch changed since its base, read from HEAD.

# ====== Standard Library Imports ======
from __future__ import annotations

import dataclasses
from fnmatch import fnmatchcase

# ====== Internal Project Imports ======
from ppdk.config.project_config import ProjectConfig
from ppdk.git.file_readers import RevisionFileReader, StagedFileReader
from ppdk.git.git_repository import GitRepository
from ppdk.rules.rule_types import FileReader, PushedRef, RuleContext, Stage


class ContextBuilder:
    """Creates the context of a stage once, then narrows it for each rule's `paths`.

    Args:
        git (GitRepository): The repository being checked.
        config (ProjectConfig): Its configuration.
    """

    # Private attributes
    _git: GitRepository
    _config: ProjectConfig

    def __init__(self, *, git: GitRepository, config: ProjectConfig) -> None:
        self._git = git
        self._config = config

    # =======================
    #   Private Methods
    # =======================
    def _changes(self, stage: Stage) -> tuple[tuple[str, ...], FileReader]:
        """Return the changed files of the stage and the reader of their content."""
        if stage is Stage.COMMIT:
            return self._git.staged_files(), StagedFileReader(self._git)
        base = self._git.base_revision(self._config.base)
        return self._git.changed_files_since(base), RevisionFileReader(self._git, "HEAD")

    # =======================
    #   Public Methods
    # =======================
    def build(self, stage: Stage, pushed_refs: tuple[PushedRef, ...] = ()) -> RuleContext:
        """Build the context shared by every rule of a stage.

        Args:
            stage (Stage): The stage being run.
            pushed_refs (tuple[PushedRef, ...]): The refs git is pushing (pre-push hook only).

        Returns:
            RuleContext: The context, with every changed file.
        """
        files, reader = self._changes(stage)
        return RuleContext(
            stage=stage,
            repo_root=self._git.root,
            base_branch=self._config.base,
            branch=self._git.current_branch(),
            changed_files=files,
            reader=reader,
            default_timeout=self._config.timeout,
            pushed_refs=pushed_refs,
        )

    @staticmethod
    def narrow(context: RuleContext, paths: tuple[str, ...]) -> RuleContext:
        """Return the context restricted to the files matching `paths` (all of them when empty).

        In the patterns, `*` also crosses folders, so `src/**` and `src/*` both mean "under src/".

        Args:
            context (RuleContext): The stage's context.
            paths (tuple[str, ...]): Glob patterns from the rule's entry.
        """
        if not paths:
            return context
        files = tuple(f for f in context.changed_files if any(fnmatchcase(f, p) for p in paths))
        return dataclasses.replace(context, changed_files=files)
