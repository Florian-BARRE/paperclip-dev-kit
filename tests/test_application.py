# ====== Code Summary ======
# End-to-end tests in real git repositories: hooks, repository rules, severities, scopes, broken
# rules, validate and init.

# ====== Standard Library Imports ======
from __future__ import annotations

import sys

# ====== Internal Project Imports ======
from ppdk import Stage
from ppdk.application import ExitCode

# ====== Local Project Imports ======
from .conftest import GitSandbox

_NO_TODO_RULE = '''
from ppdk import Finding, Rule, RuleContext, RuleResult


class NoTodoRule(Rule):
    """Refuses TODO lines."""

    def run(self, context: RuleContext) -> RuleResult:
        findings = []
        for path in context.changed_files:
            text = context.read_text(path) or ""
            for number, line in enumerate(text.splitlines(), start=1):
                if "TODO" in line:
                    findings.append(Finding("TODO left", path, number))
        return RuleResult(findings=tuple(findings))
'''


def test_repository_without_ppdk_is_left_alone(sandbox: GitSandbox) -> None:
    sandbox.switch("feature")
    assert sandbox.run("hook", "pre-commit", "") == (ExitCode.PASSED, "")


def test_commit_on_main_is_refused(sandbox: GitSandbox) -> None:
    sandbox.config('[[on.commit]]\nrule = "ppdk.base_branch"\n')
    code, report = sandbox.run("hook", "pre-commit", "")
    assert code is ExitCode.REFUSED and "base branch 'main'" in report


def test_repository_rule_reads_the_staged_version(sandbox: GitSandbox) -> None:
    sandbox.config('[[on.commit]]\nrule = "rules.no_todo"\n')
    sandbox.write(".ppdk/rules/no_todo.py", _NO_TODO_RULE)
    sandbox.switch("feature")
    sandbox.write("app.py", "x = 1  # TODO\n")
    sandbox.stage("app.py")
    # The work tree is fixed but the fix is not staged: the staged version is what is committed.
    sandbox.write("app.py", "x = 1\n")
    code, report = sandbox.run("hook", "pre-commit", "")
    assert code is ExitCode.REFUSED and "app.py:1: TODO left" in report
    sandbox.stage("app.py")
    assert sandbox.run("hook", "pre-commit", "")[0] is ExitCode.PASSED


def test_warn_severity_and_paths_scope(sandbox: GitSandbox) -> None:
    sandbox.config(
        '[[on.commit]]\nrule = "rules.no_todo"\nseverity = "warn"\n\n'
        '[[on.commit]]\nrule = "rules.no_todo"\npaths = ["docs/**"]\n'
    )
    sandbox.write(".ppdk/rules/no_todo.py", _NO_TODO_RULE)
    sandbox.switch("feature")
    sandbox.write("src/app.py", "# TODO\n")
    sandbox.stage()
    code, report = sandbox.run("hook", "pre-commit", "")
    assert code is ExitCode.PASSED
    assert "warn   rules.no_todo" in report and "skip   rules.no_todo" in report


def test_broken_rules_block_with_a_clear_message(sandbox: GitSandbox) -> None:
    sandbox.config(
        '[[on.commit]]\nrule = "rules.crashes"\n\n'
        '[[on.commit]]\nrule = "rules.missing"\n\n'
        '[[on.commit]]\nrule = "rules.two"\n'
    )
    sandbox.write(
        ".ppdk/rules/crashes.py",
        "from ppdk import Rule\n\nclass Crashes(Rule):\n    def run(self, context):\n"
        "        raise KeyError('oops')\n",
    )
    sandbox.write(
        ".ppdk/rules/two.py",
        "from ppdk import Rule, RuleResult\n\n"
        "class A(Rule):\n    def run(self, context):\n        return RuleResult.ok()\n\n"
        "class B(A):\n    pass\n",
    )
    sandbox.switch("feature")
    sandbox.stage()
    code, report = sandbox.run("check", Stage.COMMIT)
    assert code is ExitCode.REFUSED
    assert report.count("BROKEN") == 4  # three rule lines + the explanation line
    assert "KeyError('oops')" in report and "not found" in report and "found: A, B" in report


def test_push_to_main_is_refused_and_ci_uses_push_rules(sandbox: GitSandbox) -> None:
    sandbox.config('[[on.push]]\nrule = "ppdk.base_branch"\n\n[[on.push]]\nrule = "ppdk.secret"\n')
    sandbox.commit("ppdk")
    sandbox.switch("feature")
    sandbox.write("conf.py", "KEY = '" + "AKIA" + "C" * 16 + "'\n")
    sandbox.commit("leak")
    refs = "refs/heads/feature abc refs/heads/main def\n"
    code, report = sandbox.run("hook", "pre-push", refs)
    assert code is ExitCode.REFUSED and "push to the base branch" in report
    code, report = sandbox.run("check", Stage.CI)
    assert code is ExitCode.REFUSED and "conf.py:1" in report and "README.md" not in report


def test_command_rule_runs_in_the_repository(sandbox: GitSandbox) -> None:
    script = "import pathlib, sys; sys.exit(0 if pathlib.Path('README.md').exists() else 1)"
    command = f'["{sys.executable}", "-c", "{script}"]'
    sandbox.config(f'[[on.push]]\nrule = "ppdk.command"\ncommand = {command}\n')
    sandbox.switch("feature")
    assert sandbox.run("check", Stage.PUSH)[0] is ExitCode.PASSED


def test_validate_reports_every_bad_rule(sandbox: GitSandbox) -> None:
    sandbox.config(
        '[[on.commit]]\nrule = "ppdk.nope"\n\n[[on.push]]\nrule = "ppdk.file_size"\nmax_kb = "1"\n'
    )
    code, report = sandbox.run("validate")
    assert code is ExitCode.ERROR and "no such built-in rule" in report and "must be int" in report


def test_init_creates_a_valid_configuration_once(sandbox: GitSandbox) -> None:
    code, report = sandbox.run("init")
    assert code is ExitCode.PASSED and "created .ppdk/project.toml" in report
    assert sandbox.run("validate")[0] is ExitCode.PASSED
    assert sandbox.run("init")[0] is ExitCode.ERROR
