# ====== Code Summary ======
# Turns a `rule = "..."` name from project.toml into a ready Rule object: a built-in rule of the kit
# (`ppdk.<name>`) or the one Rule subclass of a repository file (`rules.<file>`, that is
# .ppdk/rules/<file>.py).

# ====== Standard Library Imports ======
from __future__ import annotations

import importlib.util
import inspect
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Final

# ====== Third-Party Library Imports ======
from loggerplusplus import LoggerClass

# ====== Internal Project Imports ======
from ppdk.config.project_config import RuleEntry
from ppdk.rules.rule import Rule, RuleConfigError

# ====== Constants ======
BUILTIN_PREFIX: Final[str] = "ppdk"
PROJECT_PREFIX: Final[str] = "rules"


class RuleLoadError(ValueError):
    """A configured rule cannot be found or does not follow the Rule contract."""


class RuleLoader(LoggerClass):
    """Finds and builds the rule each RuleEntry names.

    Args:
        builtin_rules (Mapping[str, type[Rule]]): The kit's rules, by name without prefix.
        rules_dir (Path): The repository's `.ppdk/rules` folder.
    """

    # Private attributes
    _builtin_rules: Mapping[str, type[Rule]]
    _rules_dir: Path
    _project_classes: dict[str, type[Rule]]

    def __init__(self, *, builtin_rules: Mapping[str, type[Rule]], rules_dir: Path) -> None:
        LoggerClass.__init__(self)
        self._builtin_rules = builtin_rules
        self._rules_dir = rules_dir
        self._project_classes = {}

    # =======================
    #   Private Methods
    # =======================
    def _import_file(self, name: str, path: Path) -> ModuleType:
        """Import a repository rule file as its own module."""
        # The folder above rules/ goes on sys.path so a rule can import a sibling helper
        # (`from rules._layers import LAYERS`).
        parent = str(self._rules_dir.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        module_name = f"{PROJECT_PREFIX}.{name}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise RuleLoadError(f"{module_name}: cannot import {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as error:  # boundary: a broken user file must become a clear message
            raise RuleLoadError(f"{module_name}: importing {path} failed: {error!r}") from error
        return module

    def _project_class(self, name: str) -> type[Rule]:
        """Return the single Rule subclass defined in `.ppdk/rules/<name>.py`."""
        if name in self._project_classes:
            return self._project_classes[name]
        path = self._rules_dir / f"{name}.py"
        if not path.is_file():
            raise RuleLoadError(f"{PROJECT_PREFIX}.{name}: {path} not found")
        module = self._import_file(name, path)
        # Only classes defined in the file count: an imported base class is not a candidate.
        candidates = [
            cls
            for _, cls in inspect.getmembers(module, inspect.isclass)
            if issubclass(cls, Rule)
            and cls.__module__ == module.__name__
            and not inspect.isabstract(cls)
        ]
        if len(candidates) != 1:
            found = ", ".join(cls.__name__ for cls in candidates) or "none"
            raise RuleLoadError(
                f"{PROJECT_PREFIX}.{name}: {path} must define exactly one concrete subclass of "
                f"ppdk.Rule (found: {found})"
            )
        self._project_classes[name] = candidates[0]
        return candidates[0]

    def _rule_class(self, rule: str) -> type[Rule]:
        """Return the class a configured name designates."""
        prefix, _, name = rule.partition(".")
        if prefix == BUILTIN_PREFIX:
            if name not in self._builtin_rules:
                known = ", ".join(f"{BUILTIN_PREFIX}.{n}" for n in sorted(self._builtin_rules))
                raise RuleLoadError(f"{rule}: no such built-in rule (known: {known})")
            return self._builtin_rules[name]
        if prefix == PROJECT_PREFIX and name.isidentifier():
            return self._project_class(name)
        raise RuleLoadError(
            f"{rule}: a rule is '{BUILTIN_PREFIX}.<name>' (built-in) or "
            f"'{PROJECT_PREFIX}.<file>' (.ppdk/rules/<file>.py)"
        )

    # =======================
    #   Public Methods
    # =======================
    def load(self, entry: RuleEntry) -> Rule:
        """Build the rule an entry names, with its options.

        Args:
            entry (RuleEntry): One `[[on.<stage>]]` table.

        Returns:
            Rule: The configured rule, ready to run.

        Raises:
            RuleLoadError: If the rule cannot be found, imported or built.
        """
        cls = self._rule_class(entry.rule)
        try:
            return cls(name=entry.rule, options=entry.options)
        except RuleConfigError as error:
            raise RuleLoadError(str(error)) from None
        except TypeError as error:
            raise RuleLoadError(
                f"{entry.rule}: its constructor must keep Rule's (name, options): {error}"
            ) from None
