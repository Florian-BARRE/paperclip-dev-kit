# ====== Code Summary ======
# Runs the rules of one stage in order, each isolated: a rule that cannot load or that raises is
# reported as broken instead of crashing the hook, and every rule still runs.

# ====== Standard Library Imports ======
from __future__ import annotations

import time
import traceback
import uuid

# ====== Third-Party Library Imports ======
from loggerplusplus import LoggerClass

# ====== Internal Project Imports ======
from ppdk.config.project_config import ProjectConfig, RuleEntry
from ppdk.rules.rule_types import Finding, PushedRef, RuleContext, Severity, Stage

# ====== Local Project Imports ======
from .context_builder import ContextBuilder
from .rule_loader import RuleLoader, RuleLoadError
from .stage_report import OutcomeStatus, RuleOutcome, StageReport


class StageRunner(LoggerClass):
    """Runs a stage's configured rules and collects their outcomes.

    Args:
        config (ProjectConfig): The repository's configuration.
        loader (RuleLoader): Builds each configured rule.
        contexts (ContextBuilder): Builds the stage's context and narrows it per rule.
    """

    # Private attributes
    _config: ProjectConfig
    _loader: RuleLoader
    _contexts: ContextBuilder

    def __init__(
        self, *, config: ProjectConfig, loader: RuleLoader, contexts: ContextBuilder
    ) -> None:
        LoggerClass.__init__(self)
        self._config = config
        self._loader = loader
        self._contexts = contexts

    # =======================
    #   Private Methods
    # =======================
    def _run_entry(self, entry: RuleEntry, context: RuleContext) -> RuleOutcome:
        """Load and run one rule, turning every failure into an outcome."""
        narrowed = ContextBuilder.narrow(context, entry.paths)
        if entry.paths and not narrowed.changed_files:
            return RuleOutcome(entry=entry, status=OutcomeStatus.SKIPPED)
        started = time.monotonic()
        try:
            rule = self._loader.load(entry)
            result = rule.run(narrowed)
        except RuleLoadError as error:
            return RuleOutcome(entry, OutcomeStatus.BROKEN, (Finding(message=str(error)),))
        except Exception as error:  # boundary: one broken rule must not hide the others
            self.logger.error(f"rule raised (rule={entry.rule}, error={error!r})")
            where = traceback.extract_tb(error.__traceback__)[-1]
            message = f"the rule raised {error!r} ({where.filename}:{where.lineno}): fix the rule"
            return RuleOutcome(entry, OutcomeStatus.BROKEN, (Finding(message=message),))
        seconds = time.monotonic() - started
        if result.passed:
            return RuleOutcome(entry, OutcomeStatus.PASSED, seconds=seconds)
        status = OutcomeStatus.WARNED if entry.severity is Severity.WARN else OutcomeStatus.FAILED
        return RuleOutcome(entry, status, result.findings, seconds)

    # =======================
    #   Public Methods
    # =======================
    def run(self, stage: Stage, pushed_refs: tuple[PushedRef, ...] = ()) -> StageReport:
        """Run every rule configured for `stage`.

        Args:
            stage (Stage): The stage to run.
            pushed_refs (tuple[PushedRef, ...]): The refs git is pushing (pre-push hook only).

        Returns:
            StageReport: One outcome per rule.
        """
        run_id = uuid.uuid4().hex[:8]
        entries = self._config.entries_for(stage)
        self.logger.info(
            f"START stage (run_id={run_id}, stage={stage.value}, rules={len(entries)})"
        )
        context = self._contexts.build(stage, pushed_refs)
        outcomes = tuple(self._run_entry(entry, context) for entry in entries)
        report = StageReport(stage=stage, outcomes=outcomes)
        self.logger.info(
            f"END stage (run_id={run_id}, stage={stage.value}, passed={report.passed})"
        )
        return report
