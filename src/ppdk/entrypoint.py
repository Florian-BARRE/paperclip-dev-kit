# ====== Code Summary ======
# The `ppdk` command: reads the arguments and the environment once, sets up the logs, builds the
# application and runs the requested command.

# ====== Standard Library Imports ======
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ====== Third-Party Library Imports ======
import loggerplusplus

# ====== Local Project Imports ======
from . import __version__
from .application import HOOK_STAGES, ExitCode, PpdkApplication
from .rules.builtin import BUILTIN_RULES
from .rules.rule_types import Stage


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        prog="ppdk", description="paperclip-dev-kit: git guardrails configured in .ppdk/."
    )
    parser.add_argument("--version", action="version", version=f"ppdk {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="show the kit's logs")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="run the rules of a stage")
    check.add_argument("stage", choices=[stage.value for stage in Stage])
    hook = commands.add_parser("hook", help="run as a git hook (called by the hook scripts)")
    hook.add_argument("name", choices=sorted(HOOK_STAGES))
    commands.add_parser("validate", help="check .ppdk/project.toml and load every rule")
    commands.add_parser("init", help="create a starting .ppdk/ in this repository")
    return parser.parse_args(argv)


def _setup_logs(verbose: bool) -> None:
    """Send the kit's logs to stderr: warnings only, everything with -v or PPDK_VERBOSE=1."""
    loggerplusplus.remove()
    level = "DEBUG" if verbose or os.environ.get("PPDK_VERBOSE") == "1" else "WARNING"
    loggerplusplus.add(sys.stderr, level=level)


def main(argv: list[str] | None = None) -> int:
    """Run one `ppdk` command and return its exit code (0 passed, 1 refused, 2 error)."""
    args = _parse_args(argv)
    _setup_logs(args.verbose)
    # Reports go to stderr: git shows a hook's stderr to whoever committed.
    app = PpdkApplication(cwd=Path.cwd(), builtin_rules=BUILTIN_RULES, out=sys.stderr)
    if args.command == "check":
        return app.check(Stage(args.stage))
    if args.command == "hook":
        stdin_text = "" if sys.stdin.isatty() else sys.stdin.read()
        return app.hook(args.name, stdin_text)
    if args.command == "validate":
        return app.validate()
    if args.command == "init":
        return app.init()
    return ExitCode.ERROR


if __name__ == "__main__":
    raise SystemExit(main())
