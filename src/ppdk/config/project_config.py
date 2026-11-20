# ====== Code Summary ======
# Reads a repository's .ppdk/project.toml into typed objects, and refuses a malformed file with a
# message that names the faulty key, before any rule runs.

# ====== Standard Library Imports ======
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

# ====== Third-Party Library Imports ======
from loggerplusplus import LoggerClass

# ====== Internal Project Imports ======
from ppdk.rules.rule_types import Severity, Stage

# ====== Constants ======
DEFAULT_TIMEOUT: Final[int] = 900
_ENTRY_KEYS: Final[frozenset[str]] = frozenset({"rule", "severity", "paths"})
_PROJECT_KEYS: Final[frozenset[str]] = frozenset({"base", "timeout"})
_TOP_KEYS: Final[frozenset[str]] = frozenset({"project", "on"})


class ConfigError(ValueError):
    """project.toml is missing, unreadable or malformed."""


@dataclass(frozen=True)
class RuleEntry:
    """One `[[on.<stage>]]` table: which rule runs, how strictly, on which files.

    Args:
        rule (str): `ppdk.<name>` for a built-in rule, `rules.<file>` for .ppdk/rules/<file>.py.
        severity (Severity): `error` refuses the commit or push, `warn` only reports.
        paths (tuple[str, ...]): Glob patterns; the rule only runs when a changed file matches,
            and only sees the matching files. Empty means every changed file.
        options (dict[str, object]): The other keys of the table, given to the rule.
    """

    rule: str
    severity: Severity = Severity.ERROR
    paths: tuple[str, ...] = ()
    options: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectConfig:
    """A repository's ppdk configuration.

    Args:
        root (Path): The repository root.
        base (str): The branch work merges into.
        timeout (int): Default seconds for a long check.
        stages (dict[Stage, tuple[RuleEntry, ...]]): The rules of each stage, in order.
    """

    root: Path
    base: str
    timeout: int
    stages: dict[Stage, tuple[RuleEntry, ...]]

    @property
    def rules_dir(self) -> Path:
        """The folder of the repository's own rules: `.ppdk/rules`."""
        return self.root / ".ppdk" / "rules"

    def entries_for(self, stage: Stage) -> tuple[RuleEntry, ...]:
        """Return the rules of `stage`; CI falls back to the push rules when it has none."""
        entries = self.stages.get(stage, ())
        if not entries and stage is Stage.CI:
            return self.stages.get(Stage.PUSH, ())
        return entries


class ProjectConfigLoader(LoggerClass):
    """Loads and validates `<repository>/.ppdk/project.toml`."""

    def __init__(self) -> None:
        LoggerClass.__init__(self)

    # =======================
    #   Private Methods
    # =======================
    @staticmethod
    def _unknown(keys: object, allowed: frozenset[str], where: str) -> None:
        """Raise when a table has a key the kit does not know."""
        unknown = sorted(set(keys) - allowed)  # type: ignore[arg-type]
        if unknown:
            raise ConfigError(f"{where}: unknown key(s) {', '.join(unknown)}")

    def _parse_project(self, raw: object) -> tuple[str, int]:
        """Return `base` and `timeout` from the `[project]` table."""
        if not isinstance(raw, dict):
            raise ConfigError("[project] must be a table")
        self._unknown(raw, _PROJECT_KEYS, "[project]")
        base = raw.get("base", "main")
        timeout = raw.get("timeout", DEFAULT_TIMEOUT)
        if not isinstance(base, str) or not base:
            raise ConfigError("[project] base must be a non-empty string")
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            raise ConfigError("[project] timeout must be a positive integer (seconds)")
        return base, timeout

    def _parse_entry(self, raw: object, where: str) -> RuleEntry:
        """Build one RuleEntry from a `[[on.<stage>]]` table."""
        if not isinstance(raw, dict):
            raise ConfigError(f"{where} must be a table")
        rule = raw.get("rule")
        if not isinstance(rule, str) or "." not in rule:
            raise ConfigError(f"{where}: 'rule' must be 'ppdk.<name>' or 'rules.<file>'")
        try:
            severity = Severity(raw.get("severity", Severity.ERROR.value))
        except ValueError:
            raise ConfigError(f"{where} ({rule}): severity must be 'error' or 'warn'") from None
        paths = raw.get("paths", [])
        if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
            raise ConfigError(f"{where} ({rule}): paths must be a list of glob strings")
        options = {key: value for key, value in raw.items() if key not in _ENTRY_KEYS}
        return RuleEntry(rule=rule, severity=severity, paths=tuple(paths), options=options)

    def _parse_stages(self, raw: object) -> dict[Stage, tuple[RuleEntry, ...]]:
        """Build the rules of each stage from the `[on]` table."""
        if not isinstance(raw, dict):
            raise ConfigError("[on] must hold [[on.commit]], [[on.push]] or [[on.ci]] tables")
        self._unknown(raw, frozenset(stage.value for stage in Stage), "[on]")
        stages: dict[Stage, tuple[RuleEntry, ...]] = {}
        for stage in Stage:
            tables = raw.get(stage.value, [])
            if not isinstance(tables, list):
                raise ConfigError(f"on.{stage.value} must be written [[on.{stage.value}]]")
            stages[stage] = tuple(
                self._parse_entry(table, f"[[on.{stage.value}]] #{index}")
                for index, table in enumerate(tables, start=1)
            )
        return stages

    # =======================
    #   Public Methods
    # =======================
    def load(self, root: Path) -> ProjectConfig:
        """Read and validate the configuration of the repository at `root`.

        Args:
            root (Path): The repository root.

        Returns:
            ProjectConfig: The parsed configuration.

        Raises:
            ConfigError: If the file is missing, is not valid TOML or has a wrong key or value.
        """
        path = root / ".ppdk" / "project.toml"
        if not path.is_file():
            raise ConfigError(f"{path} not found")
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(f"{path}: invalid TOML: {error}") from None
        self._unknown(raw, _TOP_KEYS, str(path))
        base, timeout = self._parse_project(raw.get("project", {}))
        stages = self._parse_stages(raw.get("on", {}))
        self.logger.debug(f"loaded config (path={path}, base={base}, timeout={timeout})")
        return ProjectConfig(root=root, base=base, timeout=timeout, stages=stages)
