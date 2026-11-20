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
# Lines of a finding shown by default: a long command output keeps its end, where failures are.
DEFAULT_FINDING_LINES: Final[int] = 60


class Reporter:
    """Renders StageReports to a text stream (the hook's stderr, so git shows it).

    Args:
        stream (TextIO): Where the report is written.
        max_finding_lines (int | None): Lines of a finding shown, from its end; None shows all.
    """

    # Private attributes
    _stream: TextIO
    _max_finding_lines: int | None

    def __init__(
        self, stream: TextIO, max_finding_lines: int | None = DEFAULT_FINDING_LINES
    ) -> None:
        self._stream = stream
        self._max_finding_lines = max_finding_lines

    # =======================
    #   Private Methods
    # =======================
    def _write(self, text: str = "") -> None:
        """Write one line of the report."""
        self._stream.write(f"{text}\n")

    def _write_body(self, lines: list[str]) -> None:
        """Write a finding's following lines, keeping only the last ones when they are too many."""
        limit = self._max_finding_lines
        if limit is not None and len(lines) > limit:
            hidden = len(lines) - limit
            self._write(f"{_INDENT}  [... {hidden} line(s) hidden: rerun with --full-output ...]")
            lines = lines[-limit:]
        for line in lines:
            self._write(f"{_INDENT}  {line}")

    def _write_outcome(self, outcome: RuleOutcome) -> None:
        """Write one rule's line and its findings."""
        suffix = " (no matching file)" if outcome.status is OutcomeStatus.SKIPPED else ""
        self._write(f"  {_LABELS[outcome.status]} {outcome.entry.rule}{suffix}")
        for finding in outcome.findings:
            location = finding.location()
            lines = finding.message.splitlines() or [""]
            head = f"{location}: {lines[0]}" if location else lines[0]
            self._write(f"{_INDENT}{head}")
            self._write_body(lines[1:])

    # =======================
    #   Public Methods
    # =======================
    def write(self, report: StageReport) -> None:
        """Write the whole report, ending with the verdict.

        Args:
            report (StageReport): The outcomes of a stage.
        """
        stage = report.stage.value
        # A clean pass stays one line: hooks run at every commit, noise would hide real reports.
        if report.passed and not any(o.status is OutcomeStatus.WARNED for o in report.outcomes):
            self._write(f"ppdk {stage}: passed ({len(report.outcomes)} rule(s))")
            return
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
