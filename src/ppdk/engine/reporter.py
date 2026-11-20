# ====== Code Summary ======
# Writes a stage report for the agent (or person) who committed: each rule's status, every finding
# with its location, and what to do next.

# ====== Standard Library Imports ======
from __future__ import annotations

from typing import Final, TextIO

# ====== Local Project Imports ======
from .stage_report import OutcomeStatus, RuleOutcome, StageReport

# ====== Constants ======
_LABELS: Final[dict[OutcomeStatus, str]] = {
    OutcomeStatus.PASSED: "ok    ",
    OutcomeStatus.FAILED: "FAIL  ",
    OutcomeStatus.WARNED: "warn  ",
    OutcomeStatus.SKIPPED: "skip  ",
    OutcomeStatus.BROKEN: "BROKEN",
}
_INDENT: Final[str] = "         "


class Reporter:
    """Renders StageReports to a text stream (the hook's stderr, so git shows it).

    Args:
        stream (TextIO): Where the report is written.
    """

    # Private attributes
    _stream: TextIO

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    # =======================
    #   Private Methods
    # =======================
    def _write(self, text: str = "") -> None:
        """Write one line of the report."""
        self._stream.write(f"{text}\n")

    def _write_outcome(self, outcome: RuleOutcome) -> None:
        """Write one rule's line and its findings."""
        suffix = " (no matching file)" if outcome.status is OutcomeStatus.SKIPPED else ""
        self._write(f"  {_LABELS[outcome.status]} {outcome.entry.rule}{suffix}")
        for finding in outcome.findings:
            location = finding.location()
            lines = finding.message.splitlines() or [""]
            head = f"{location}: {lines[0]}" if location else lines[0]
            self._write(f"{_INDENT}{head}")
            for line in lines[1:]:
                self._write(f"{_INDENT}  {line}")

    # =======================
    #   Public Methods
    # =======================
    def write(self, report: StageReport) -> None:
        """Write the whole report, ending with the verdict.

        Args:
            report (StageReport): The outcomes of a stage.
        """
        stage = report.stage.value
        self._write(f"ppdk {stage}: {len(report.outcomes)} rule(s)")
        for outcome in report.outcomes:
            self._write_outcome(outcome)
        if report.passed:
            self._write(f"ppdk {stage}: passed")
            return
        broken = any(o.status is OutcomeStatus.BROKEN for o in report.blocking)
        self._write(
            f"ppdk {stage}: refused, {len(report.blocking)} rule(s) blocking. Fix every finding "
            f"above, then run the {stage} again. Never bypass the check (--no-verify)."
        )
        if broken:
            self._write(
                "A BROKEN rule is a bug in the rule or its configuration (.ppdk/): fix it, or "
                "report it to your lead if it is not yours to change."
            )

    def write_error(self, message: str) -> None:
        """Write an error that prevented any rule from running (configuration, git)."""
        self._write(f"ppdk: {message}")
