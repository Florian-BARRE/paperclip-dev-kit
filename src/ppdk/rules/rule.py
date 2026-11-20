# ====== Code Summary ======
# The contract every rule follows, built-in or written in a repository's .ppdk/rules/: options read
# and checked once in the constructor, then `run(context)` returns a RuleResult.

# ====== Standard Library Imports ======
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import ClassVar, TypeVar

# ====== Third-Party Library Imports ======
from loggerplusplus import LoggerClass

# ====== Local Project Imports ======
from .rule_types import RuleContext, RuleResult

# ====== Type Hints ======
OptionType = TypeVar("OptionType")


class RuleConfigError(ValueError):
    """A rule's options in project.toml are wrong: unknown, missing or of the wrong type."""


class Rule(ABC, LoggerClass):
    """Base class of every rule.

    A rule is one check run at a stage (commit, push, CI). Subclasses:

    - declare the options they accept in `OPTIONS` (any other key in project.toml is refused);
    - read and validate them in `_configure` with `_option`, so a bad configuration fails before
      anything runs;
    - implement `run`, which only looks at the context and returns a RuleResult.

    Args:
        name (str): The name the rule is configured under (`ppdk.secret`, `rules.structure_check`).
        options (Mapping[str, object] | None): The rule's keys from its `[[on.<stage>]]` table,
            without `rule`, `severity` and `paths`.

    Raises:
        RuleConfigError: If an option is unknown or invalid.

    Examples:
        >>> class NoPrintRule(Rule):
        ...     def run(self, context: RuleContext) -> RuleResult:
        ...         return RuleResult.ok()
    """

    # Option names this rule accepts; subclasses override it.
    OPTIONS: ClassVar[frozenset[str]] = frozenset()

    # Public attributes
    name: str
    options: dict[str, object]

    def __init__(self, *, name: str, options: Mapping[str, object] | None = None) -> None:
        LoggerClass.__init__(self, identifier=name)
        self.name = name
        self.options = dict(options or {})
        unknown = sorted(set(self.options) - self.OPTIONS)
        if unknown:
            accepted = ", ".join(sorted(self.OPTIONS)) or "none"
            raise RuleConfigError(
                f"{name}: unknown option(s) {', '.join(unknown)} (accepted: {accepted})"
            )
        self._configure()

    # =======================
    #   Private Methods
    # =======================
    def _configure(self) -> None:
        """Read and validate the options; the default rule has none."""

    def _option(
        self, key: str, expected: type[OptionType], default: OptionType | None = None
    ) -> OptionType:
        """Return option `key`, checked against `expected`, or `default` when it is absent.

        Args:
            key (str): The option name, one of `OPTIONS`.
            expected (type): The type the value must have (`str`, `int`, `list`...).
            default: The value when the option is absent; None makes the option required.

        Raises:
            RuleConfigError: If the option is required and absent, or has the wrong type.
        """
        if key not in self.options:
            if default is None:
                raise RuleConfigError(f"{self.name}: option '{key}' is required")
            return default
        value = self.options[key]
        # bool is an int in Python: refuse it where a number is expected.
        if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
            raise RuleConfigError(
                f"{self.name}: option '{key}' must be {expected.__name__}, "
                f"got {type(value).__name__}"
            )
        return value

    def _string_list_option(self, key: str, default: list[str] | None = None) -> list[str]:
        """Return option `key` as a list of strings (see `_option`).

        Raises:
            RuleConfigError: If the value is not a list of strings.
        """
        values = self._option(key, list, default)
        if not all(isinstance(item, str) for item in values):
            raise RuleConfigError(f"{self.name}: option '{key}' must be a list of strings")
        return list(values)

    # =======================
    #   Public Methods
    # =======================
    @abstractmethod
    def run(self, context: RuleContext) -> RuleResult:
        """Check the change described by `context`.

        Args:
            context (RuleContext): The stage, the changed files and a reader for their content.

        Returns:
            RuleResult: `RuleResult.ok()`, or `RuleResult.fail(Finding(...), ...)`.
        """
