# ====== Code Summary ======
# The result of running a stage: one outcome per configured rule, and whether the stage lets the
# commit or push through.

# ====== Standard Library Imports ======
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ====== Internal Project Imports ======
from ppdk.config.project_config import RuleEntry
from ppdk.rules.rule_types import Finding, Stage


class OutcomeStatus(str, Enum):
    """What happened to one rule."""

    PASSED = "passed"
    FAILED = "failed"  # findings on an `error` rule: blocks
    WARNED = "warned"  # findings on a `warn` rule: reported, does not block
    SKIPPED = "skipped"  # the rule has `paths` and no changed file matches
    BROKEN = "broken"  # the rule could not be loaded or raised: blocks, the rule must be fixed


@dataclass(frozen=True)
class RuleOutcome:
    """One rule's outcome in a stage.

    Args:
        entry (RuleEntry): The configured rule.
        status (OutcomeStatus): What happened.
        findings (tuple[Finding, ...]): The problems found, or the error that broke the rule.
        seconds (float): How long the rule took.
    """

    entry: RuleEntry
    status: OutcomeStatus
    findings: tuple[Finding, ...] = ()
    seconds: float = 0.0

    @property
    def blocks(self) -> bool:
        """True when this outcome refuses the commit or push."""
        return self.status in (OutcomeStatus.FAILED, OutcomeStatus.BROKEN)


@dataclass(frozen=True)
class StageReport:
    """Every rule's outcome for one stage.

    Args:
        stage (Stage): The stage run.
        outcomes (tuple[RuleOutcome, ...]): One outcome per configured rule, in order.
    """

    stage: Stage
    outcomes: tuple[RuleOutcome, ...]

    @property
    def passed(self) -> bool:
        """True when no rule blocks."""
        return not any(outcome.blocks for outcome in self.outcomes)

    @property
    def blocking(self) -> tuple[RuleOutcome, ...]:
        """The outcomes that block."""
        return tuple(outcome for outcome in self.outcomes if outcome.blocks)
