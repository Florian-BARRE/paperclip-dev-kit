# ====== Code Summary ======
# Tests of the .ppdk/project.toml loader: defaults, entries, CI fallback and precise errors.

# ====== Standard Library Imports ======
from __future__ import annotations

from pathlib import Path

# ====== Third-Party Library Imports ======
import pytest

# ====== Internal Project Imports ======
from ppdk import Severity, Stage
from ppdk.config import ConfigError, ProjectConfigLoader


def _load(tmp_path: Path, toml: str):
    (tmp_path / ".ppdk").mkdir()
    (tmp_path / ".ppdk" / "project.toml").write_text(toml, encoding="utf-8")
    return ProjectConfigLoader().load(tmp_path)


def test_entries_options_and_defaults(tmp_path: Path) -> None:
    config = _load(
        tmp_path,
        """
[project]
base = "develop"

[[on.commit]]
rule = "rules.structure"
severity = "warn"
paths = ["src/**"]
depth = 3
""",
    )
    entry = config.entries_for(Stage.COMMIT)[0]
    assert config.base == "develop" and config.timeout == 900
    assert entry.severity is Severity.WARN and entry.paths == ("src/**",)
    assert entry.options == {"depth": 3}


def test_ci_falls_back_to_push_rules(tmp_path: Path) -> None:
    config = _load(tmp_path, '[[on.push]]\nrule = "ppdk.secret"\n')
    assert [e.rule for e in config.entries_for(Stage.CI)] == ["ppdk.secret"]


@pytest.mark.parametrize(
    ("toml", "message"),
    [
        ("[project]\nbranch = 'main'\n", "unknown key"),
        ("[[on.deploy]]\nrule = 'ppdk.secret'\n", "unknown key"),
        ("[[on.commit]]\nrule = 'secret'\n", "'rule' must be"),
        ("[[on.commit]]\nrule = 'ppdk.secret'\nseverity = 'fatal'\n", "severity"),
        ("[[on.commit]]\nrule = 'ppdk.secret'\npaths = 'src'\n", "paths"),
        ("[project]\ntimeout = 0\n", "timeout"),
        ("[on]\ncommit = 'x'\n", "[[on.commit]]"),
        ("not toml =", "invalid TOML"),
    ],
)
def test_malformed_files_name_the_problem(tmp_path: Path, toml: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message.replace("[", r"\[").replace("]", r"\]")):
        _load(tmp_path, toml)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        ProjectConfigLoader().load(tmp_path)
