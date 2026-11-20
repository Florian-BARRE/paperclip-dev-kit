# ====== Code Summary ======
# The kit's commands (check a stage, run as a git hook, validate a configuration, scaffold .ppdk/),
# assembled from the engine; each returns the process exit code.

# ====== Standard Library Imports ======
from __future__ import annotations

from collections.abc import Mapping
from enum import IntEnum
from pathlib import Path
from typing import Final, TextIO

# ====== Third-Party Library Imports ======
from loggerplusplus import LoggerClass

# ====== Local Project Imports ======
from .config.project_config import ConfigError, ProjectConfig, ProjectConfigLoader
from .engine.context_builder import ContextBuilder
from .engine.reporter import DEFAULT_FINDING_LINES, Reporter
from .engine.rule_loader import RuleLoader, RuleLoadError
from .engine.stage_runner import StageRunner
from .git.git_repository import GitError, GitRepository
from .rules.rule import Rule
from .rules.rule_types import PushedRef, Stage
from .scaffold import Scaffold

# ====== Constants ======
HOOK_STAGES: Final[dict[str, Stage]] = {"pre-commit": Stage.COMMIT, "pre-push": Stage.PUSH}


class ExitCode(IntEnum):
    """The process exit codes of every command."""

    PASSED = 0
    REFUSED = 1  # a rule blocks: the commit or push must not happen
    ERROR = 2  # the kit could not run: no repository, bad configuration


class PpdkApplication(LoggerClass):
    """Runs the kit's commands in the repository that contains `cwd`.

    Args:
        cwd (Path): Where the command was started.
        builtin_rules (Mapping[str, type[Rule]]): The kit's rules.
        out (TextIO): Where reports go (stderr in hooks, so git shows them).
        full_output (bool): Show every line of the findings (a command's whole output).
    """

    # Private attributes
    _cwd: Path
    _builtin_rules: Mapping[str, type[Rule]]
    _reporter: Reporter

    def __init__(
        self,
        *,
        cwd: Path,
        builtin_rules: Mapping[str, type[Rule]],
        out: TextIO,
        full_output: bool = False,
    ) -> None:
        LoggerClass.__init__(self)
        self._cwd = cwd
        self._builtin_rules = builtin_rules
        self._reporter = Reporter(out, None if full_output else DEFAULT_FINDING_LINES)

    # =======================
    #   Private Methods
    # =======================
    def _repository(self) -> tuple[GitRepository, ProjectConfig]:
        """Return the repository and its configuration.

        Raises:
            GitError: If not inside a git repository.
            ConfigError: If .ppdk/project.toml is missing or malformed.
        """
        git = GitRepository.discover(self._cwd)
        return git, ProjectConfigLoader().load(git.root)

    def _loader(self, config: ProjectConfig) -> RuleLoader:
        """Build the rule loader of a repository."""
        return RuleLoader(builtin_rules=self._builtin_rules, rules_dir=config.rules_dir)

    @staticmethod
    def _parse_pushed_refs(lines: str) -> tuple[PushedRef, ...]:
        """Parse git's pre-push input: `<local ref> <local sha> <remote ref> <remote sha>` lines."""
        refs: list[PushedRef] = []
        for line in lines.splitlines():
            parts = line.split()
            # A deletion has "(delete)" as local ref: it changes no content, nothing to check.
            if len(parts) == 4 and parts[0] != "(delete)":
                refs.append(PushedRef(local_ref=parts[0], remote_ref=parts[2]))
        return tuple(refs)

    # =======================
    #   Public Methods
    # =======================
    def check(self, stage: Stage, pushed_refs: tuple[PushedRef, ...] = ()) -> ExitCode:
        """Run the rules of `stage` and write the report.

        Args:
            stage (Stage): The stage to run.
            pushed_refs (tuple[PushedRef, ...]): The refs git is pushing, when known.

        Returns:
            ExitCode: PASSED, REFUSED when a rule blocks, ERROR when the kit cannot run.
        """
        try:
            git, config = self._repository()
        except (GitError, ConfigError) as error:
            self._reporter.write_error(str(error))
            return ExitCode.ERROR
        runner = StageRunner(
            config=config,
            loader=self._loader(config),
            contexts=ContextBuilder(git=git, config=config),
        )
        report = runner.run(stage, pushed_refs)
        self._reporter.write(report)
        return ExitCode.PASSED if report.passed else ExitCode.REFUSED

    def hook(self, hook_name: str, stdin_text: str) -> ExitCode:
        """Run as git hook `hook_name`; a repository without .ppdk/ is left alone.

        Args:
            hook_name (str): `pre-commit` or `pre-push`.
            stdin_text (str): What git wrote on the hook's standard input.

        Returns:
            ExitCode: As `check`; PASSED when the repository does not use ppdk.
        """
        try:
            git = GitRepository.discover(self._cwd)
        except GitError as error:
            self._reporter.write_error(str(error))
            return ExitCode.ERROR
        if not (git.root / ".ppdk" / "project.toml").is_file():
            return ExitCode.PASSED
        return self.check(HOOK_STAGES[hook_name], self._parse_pushed_refs(stdin_text))

    def validate(self) -> ExitCode:
        """Check the configuration and build every configured rule, without running them.

        Returns:
            ExitCode: PASSED when every rule loads, ERROR otherwise.
        """
        try:
            _, config = self._repository()
        except (GitError, ConfigError) as error:
            self._reporter.write_error(str(error))
            return ExitCode.ERROR
        loader = self._loader(config)
        errors: list[str] = []
        for stage in Stage:
            for entry in config.stages.get(stage, ()):
                try:
                    loader.load(entry)
                except RuleLoadError as error:
                    errors.append(f"[[on.{stage.value}]] {error}")
        for error in errors:
            self._reporter.write_error(error)
        if errors:
            return ExitCode.ERROR
        total = sum(len(entries) for entries in config.stages.values())
        self._reporter.write_error(f"configuration valid ({total} rule(s))")
        return ExitCode.PASSED

    def init(self) -> ExitCode:
        """Create .ppdk/project.toml and .ppdk/rules/ in the repository, never overwriting.

        Returns:
            ExitCode: PASSED when created, ERROR when outside a repository or already there.
        """
        try:
            git = GitRepository.discover(self._cwd)
            created = Scaffold(git.root).create()
        except (GitError, FileExistsError) as error:
            self._reporter.write_error(str(error))
            return ExitCode.ERROR
        for path in created:
            self._reporter.write_error(f"created {path.relative_to(git.root)}")
        return ExitCode.PASSED
