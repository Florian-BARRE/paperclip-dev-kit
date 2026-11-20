# ====== Code Summary ======
# Tests of the report: a clean pass is one line, long findings keep their end unless asked for all.

# ====== Standard Library Imports ======
from __future__ import annotations

import io

# ====== Internal Project Imports ======
from ppdk import Finding, Stage
from ppdk.config import RuleEntry
from ppdk.engine import OutcomeStatus, Reporter, RuleOutcome, StageReport


def _report(status: OutcomeStatus, message: str = "") -> StageReport:
    findings = (Finding(message),) if message else ()
    outcome = RuleOutcome(RuleEntry(rule="ppdk.command"), status, findings)
    return StageReport(stage=Stage.PUSH, outcomes=(outcome,))


def test_a_clean_pass_is_one_line() -> None:
    out = io.StringIO()
    Reporter(out).write(_report(OutcomeStatus.PASSED))
    assert out.getvalue() == "ppdk push: passed (1 rule(s))\n"


def test_a_long_finding_keeps_its_end_unless_full_output() -> None:
    message = "cmd failed:\n" + "\n".join(f"line {n}" for n in range(1, 101))
    short, full = io.StringIO(), io.StringIO()
    Reporter(short, max_finding_lines=10).write(_report(OutcomeStatus.FAILED, message))
    Reporter(full, max_finding_lines=None).write(_report(OutcomeStatus.FAILED, message))
    assert "90 line(s) hidden" in short.getvalue() and "line 100" in short.getvalue()
    assert "line 90\n" not in short.getvalue()
    assert "line 1\n" in full.getvalue() and "hidden" not in full.getvalue()
