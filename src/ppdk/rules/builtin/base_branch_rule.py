# ====== Code Summary ======
# Built-in rule ppdk.base_branch: work goes through a branch and a pull request, never straight onto
# the base branch (no commit on it, no push to it).

# ====== Standard Library Imports ======
from __future__ import annotations

# ====== Local Project Imports ======
from ..rule import Rule
from ..rule_types import Finding, RuleContext, RuleResult, Stage


class BaseBranchRule(Rule):
    """Refuses a commit on the base branch and a push that updates it; passes in CI."""

    # =======================
    #   Private Methods
    # =======================
    def _check_commit(self, context: RuleContext) -> RuleResult:
        """Refuse when the current branch is the base branch."""
        if context.branch == context.base_branch:
            return RuleResult.fail(
                Finding(
                    message=(
                        f"commit on the base branch '{context.base_branch}': create a branch "
                        "(git switch -c <name>), commit there, then open a pull request"
                    )
                )
            )
        return RuleResult.ok()

    def _check_push(self, context: RuleContext) -> RuleResult:
        """Refuse when a pushed ref updates the base branch on the remote."""
        target = f"refs/heads/{context.base_branch}"
        if any(ref.remote_ref == target for ref in context.pushed_refs):
            return RuleResult.fail(
                Finding(
                    message=(
                        f"push to the base branch '{context.base_branch}': push your branch "
                        "and open a pull request instead"
                    )
                )
            )
        # Without git's ref list (a manual `ppdk check push`), the current branch decides.
        if not context.pushed_refs:
            return self._check_commit(context)
        return RuleResult.ok()

    # =======================
    #   Public Methods
    # =======================
    def run(self, context: RuleContext) -> RuleResult:
        """Check the branch for the stage.

        Args:
            context (RuleContext): The stage, the branch and the pushed refs.

        Returns:
            RuleResult: A failure on the base branch, a pass otherwise (always a pass in CI).
        """
        if context.stage is Stage.COMMIT:
            return self._check_commit(context)
        if context.stage is Stage.PUSH:
            return self._check_push(context)
        return RuleResult.ok()
