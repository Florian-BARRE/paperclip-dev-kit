"""Running a stage: loading the rules, building their context, collecting and reporting outcomes."""

from .context_builder import ContextBuilder
from .reporter import Reporter
from .rule_loader import RuleLoader, RuleLoadError
from .stage_report import OutcomeStatus, RuleOutcome, StageReport
from .stage_runner import StageRunner

__all__ = [
    "ContextBuilder",
    "OutcomeStatus",
    "Reporter",
    "RuleLoadError",
    "RuleLoader",
    "RuleOutcome",
    "StageReport",
    "StageRunner",
]
