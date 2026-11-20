# ====== Code Summary ======
# `ppdk init`: writes a starting .ppdk/ (project.toml with the built-in safety rules, and an example
# repository rule) into a repository that has none.

# ====== Standard Library Imports ======
from __future__ import annotations

from pathlib import Path
from typing import Final

# ====== Constants ======
_PROJECT_TOML: Final[str] = """\
# paperclip-dev-kit: the checks git runs in this repository.
# Docs: https://github.com/Florian-BARRE/paperclip-dev-kit
# Each [[on.<stage>]] table runs one rule: "ppdk.<name>" (built into the kit) or "rules.<file>"
# (.ppdk/rules/<file>.py). Keys: severity = "error" (default, blocks) or "warn"; paths = globs the
# rule is limited to; any other key is an option of the rule.

[project]
base = "main"     # the branch work merges into
timeout = 900     # default seconds for a long check (ppdk.command)

# ---- At each commit: fast checks only (seconds) ----
[[on.commit]]
rule = "ppdk.base_branch"

[[on.commit]]
rule = "ppdk.env_file"

[[on.commit]]
rule = "ppdk.secret"

[[on.commit]]
rule = "ppdk.conflict_marker"

[[on.commit]]
rule = "ppdk.file_size"
max_kb = 1024

# [[on.commit]]
# rule = "rules.example_rule"
# paths = ["src/**"]

# ---- Before each push: the complete checks ----
[[on.push]]
rule = "ppdk.base_branch"

# [[on.push]]
# rule = "ppdk.command"
# command = ["uv", "run", "pytest"]

# ---- In CI: [[on.ci]] tables; without any, CI runs the push rules ----
"""

_EXAMPLE_RULE: Final[str] = '''\
# ====== Code Summary ======
# Example repository rule: copy it, rename the file and the class, then enable it in project.toml
# with rule = "rules.<file name>".

# ====== Standard Library Imports ======
from __future__ import annotations

# ====== Third-Party Library Imports ======
from ppdk import Finding, Rule, RuleContext, RuleResult


class ExampleRule(Rule):
    """Refuses a changed Python file that contains a debugging print."""

    def run(self, context: RuleContext) -> RuleResult:
        """Check every changed Python file."""
        findings = []
        for path in context.changed_files:
            text = context.read_text(path)
            if not path.endswith(".py") or text is None:
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                if line.strip().startswith("print("):
                    findings.append(Finding("debugging print: use the logger", path, number))
        return RuleResult(findings=tuple(findings))
'''


class Scaffold:
    """Creates a repository's starting .ppdk/ folder.

    Args:
        root (Path): The repository root.
    """

    # Private attributes
    _root: Path

    def __init__(self, root: Path) -> None:
        self._root = root

    def create(self) -> list[Path]:
        """Write .ppdk/project.toml and .ppdk/rules/example_rule.py.

        Returns:
            list[Path]: The files created.

        Raises:
            FileExistsError: If .ppdk/project.toml already exists (nothing is overwritten).
        """
        config = self._root / ".ppdk" / "project.toml"
        if config.exists():
            raise FileExistsError(f"{config} already exists")
        rule = self._root / ".ppdk" / "rules" / "example_rule.py"
        rule.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(_PROJECT_TOML, encoding="utf-8")
        rule.write_text(_EXAMPLE_RULE, encoding="utf-8")
        return [config, rule]
