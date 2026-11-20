# ====== Code Summary ======
# Built-in rule ppdk.command: runs one of the repository's own commands (its unit tests, a linter)
# from the repository root and fails when it exits non-zero.

# ====== Standard Library Imports ======
from __future__ import annotations

import re
import subprocess
from typing import ClassVar, Final

# ====== Local Project Imports ======
from ..rule import Rule, RuleConfigError
from ..rule_types import Finding, RuleContext, RuleResult

# ====== Constants ======
# Colour codes make a report unreadable once captured: they are removed from the output.
_ANSI_ESCAPE: Final[re.Pattern[str]] = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


class CommandRule(Rule):
    """Runs a command and fails when it exits non-zero or takes too long.

    Options:
        command (list[str]): The command and its arguments, run without a shell.
        timeout (int): Seconds before it is stopped (default: `[project] timeout`).
    """

    OPTIONS: ClassVar[frozenset[str]] = frozenset({"command", "timeout"})

    # Private attributes
    _command: list[str]
    _timeout: int | None

    # =======================
    #   Private Methods
    # =======================
    def _configure(self) -> None:
        """Read the command and its timeout."""
        self._command = self._string_list_option("command")
        if not self._command:
            raise RuleConfigError(f"{self.name}: option 'command' must not be empty")
        self._timeout = self._option("timeout", int, 0) or None

    @staticmethod
    def _clean(output: str) -> str:
        """Return `output` without colour codes and surrounding blank lines."""
        return _ANSI_ESCAPE.sub("", output).strip()

    # =======================
    #   Public Methods
    # =======================
    def run(self, context: RuleContext) -> RuleResult:
        """Run the command in the repository root.

        Args:
            context (RuleContext): The repository root and the default timeout.

        Returns:
            RuleResult: A failure carrying the command's output when it fails.
        """
        timeout = self._timeout or context.default_timeout
        shown = " ".join(self._command)
        self.logger.info(f"START command (cmd={shown}, timeout={timeout}s)")
        try:
            completed = subprocess.run(
                self._command,
                cwd=context.repo_root,
                # One stream, in the order it was written: a failure stays next to its context.
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except OSError as error:
            # Missing program, missing working directory, permission denied.
            return RuleResult.fail(Finding(message=f"cannot start `{shown}`: {error.strerror}"))
        except subprocess.TimeoutExpired:
            return RuleResult.fail(Finding(message=f"`{shown}` took more than {timeout}s"))
        self.logger.info(f"END command (cmd={shown}, exit={completed.returncode})")
        if completed.returncode == 0:
            return RuleResult.ok()
        # The whole output goes in the finding; the report decides how much of it to show.
        output = self._clean(completed.stdout or "")
        return RuleResult.fail(
            Finding(message=f"`{shown}` failed (exit {completed.returncode}):\n{output}")
        )
