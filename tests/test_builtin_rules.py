# ====== Code Summary ======
# Unit tests of the built-in rules, on in-memory contexts (no git).

# ====== Standard Library Imports ======
from __future__ import annotations

import dataclasses
import sys

# ====== Third-Party Library Imports ======
import pytest

# ====== Internal Project Imports ======
from ppdk import PushedRef, RuleConfigError, Stage
from ppdk.rules.builtin import (
    BaseBranchRule,
    CommandRule,
    ConflictMarkerRule,
    EnvFileRule,
    FileSizeRule,
    SecretRule,
)

# ====== Local Project Imports ======
from .conftest import make_context


def test_base_branch_refuses_a_commit_on_main_only() -> None:
    rule = BaseBranchRule(name="ppdk.base_branch")
    assert not rule.run(make_context({}, branch="main")).passed
    assert rule.run(make_context({}, branch="feature")).passed


def test_base_branch_refuses_a_push_that_updates_main() -> None:
    rule = BaseBranchRule(name="ppdk.base_branch")
    context = make_context({}, stage=Stage.PUSH)
    to_main = (PushedRef("refs/heads/feature", "refs/heads/main"),)
    to_feature = (PushedRef("refs/heads/feature", "refs/heads/feature"),)
    assert not rule.run(dataclasses.replace(context, pushed_refs=to_main)).passed
    assert rule.run(dataclasses.replace(context, pushed_refs=to_feature)).passed


def test_base_branch_passes_in_ci() -> None:
    rule = BaseBranchRule(name="ppdk.base_branch")
    assert rule.run(make_context({}, stage=Stage.CI, branch="main")).passed


def test_env_file_refuses_env_files_but_allows_the_example() -> None:
    rule = EnvFileRule(name="ppdk.env_file")
    result = rule.run(make_context({".env": b"A=1", "app/.env.prod": b"", ".env.example": b""}))
    assert sorted(f.path for f in result.findings) == [".env", "app/.env.prod"]


def test_env_file_allow_option() -> None:
    rule = EnvFileRule(name="ppdk.env_file", options={"allow": [".env.test"]})
    assert rule.run(make_context({".env.test": b""})).passed


def test_secret_finds_known_formats_and_extra_patterns() -> None:
    fake_key = "AKIA" + "B" * 16
    rule = SecretRule(name="ppdk.secret", options={"patterns": [r"INTERNAL-[0-9]{4}"]})
    result = rule.run(make_context({"a.py": f"x = '{fake_key}'\nok\nINTERNAL-1234\n".encode()}))
    assert [f.line for f in result.findings] == [1, 3]


def test_secret_rejects_an_invalid_pattern() -> None:
    with pytest.raises(RuleConfigError, match="invalid pattern"):
        SecretRule(name="ppdk.secret", options={"patterns": ["("]})


def test_conflict_marker_ignores_markdown_underlines_and_binary_files() -> None:
    rule = ConflictMarkerRule(name="ppdk.conflict_marker")
    files = {"a.txt": b"<<<<<<< HEAD\nx\n=======\n>>>>>>> b\n", "b.md": b"Title\n=======\n"}
    files["c.bin"] = b"\0<<<<<<< HEAD"
    assert [(f.path, f.line) for f in rule.run(make_context(files)).findings] == [
        ("a.txt", 1),
        ("a.txt", 4),
    ]


def test_file_size_limit() -> None:
    rule = FileSizeRule(name="ppdk.file_size", options={"max_kb": 1})
    result = rule.run(make_context({"big.bin": b"x" * 2048, "small.txt": b"x"}))
    assert [f.path for f in result.findings] == ["big.bin"]


@pytest.mark.parametrize("options", [{"max_kb": 0}, {"max_kb": "1"}, {"max_kb": True}])
def test_file_size_refuses_bad_limits(options: dict[str, object]) -> None:
    with pytest.raises(RuleConfigError):
        FileSizeRule(name="ppdk.file_size", options=options)


def test_command_passes_fails_and_times_out() -> None:
    ok = CommandRule(name="ppdk.command", options={"command": [sys.executable, "-c", "pass"]})
    assert ok.run(make_context({})).passed
    failing = CommandRule(
        name="ppdk.command",
        options={"command": [sys.executable, "-c", "print('boom'); raise SystemExit(3)"]},
    )
    finding = failing.run(make_context({})).findings[0]
    assert "exit 3" in finding.message and "boom" in finding.message
    slow = CommandRule(
        name="ppdk.command",
        options={"command": [sys.executable, "-c", "import time; time.sleep(5)"], "timeout": 1},
    )
    assert "more than 1s" in slow.run(make_context({})).findings[0].message


def test_command_requires_a_command_and_reports_a_missing_program() -> None:
    with pytest.raises(RuleConfigError, match="required"):
        CommandRule(name="ppdk.command")
    missing = CommandRule(name="ppdk.command", options={"command": ["no-such-program-ppdk"]})
    assert "cannot start" in missing.run(make_context({})).findings[0].message


def test_unknown_option_is_refused() -> None:
    with pytest.raises(RuleConfigError, match="unknown option"):
        ConflictMarkerRule(name="ppdk.conflict_marker", options={"strict": True})
