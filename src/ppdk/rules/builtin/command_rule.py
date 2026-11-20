# ====== Code Summary ======
# Built-in rule ppdk.command: runs one of the repository's own commands (its unit tests, a linter)
# from the repository root and fails when it exits non-zero.

# ====== Standard Library Imports ======
from __future__ import annotations

import subprocess
from typing import ClassVar, Final

# ====== Local Project Imports ======
from ..rule import Rule, RuleConfigError
from ..rule_types import Finding, RuleContext, RuleResult

# ====== Constants ======
# Lines of output kept in the report: enough to see the failure, not the whole log.
_OUTPUT_TAIL_LINES: Final[int] = 40


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
    def _tail(output: str) -> str:
        """Return the last lines of `output`."""
        lines = output.strip().splitlines()
        return "\n".join(lines[-_OUTPUT_TAIL_LINES:])

    # =======================
    #   Public Methods
    # =======================
    def run(self, context: RuleContext) -> RuleResult:
        """Run the command in the repository root.

        Args:
            context (RuleContext): The repository root and the default timeout.

        Returns:
            RuleResult: A failure with the end of the output when the command fails.
        """
        timeout = self._timeout or context.default_timeout
        shown = " ".join(self._command)
        self.logger.info(f"START command (cmd={shown}, timeout={timeout}s)")
        try:
            completed = subprocess.run(
                self._command,
                cwd=context.repo_root,
                capture_output=True,
                text=True,
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
        output = self._tail(f"{completed.stdout}\n{completed.stderr}")
        return RuleResult.fail(
            Finding(message=f"`{shown}` failed (exit {completed.returncode}):\n{output}")
        )
