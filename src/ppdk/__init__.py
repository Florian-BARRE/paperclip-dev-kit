"""paperclip-dev-kit: git guardrails for coding agents.

A repository rule imports everything it needs from here:

    from ppdk import Finding, Rule, RuleContext, RuleResult
"""

from .rules import (
    FileReader,
    Finding,
    PushedRef,
    Rule,
    RuleConfigError,
    RuleContext,
    RuleResult,
    Severity,
    Stage,
)

__version__ = "0.1.0"

__all__ = [
    "FileReader",
    "Finding",
    "PushedRef",
    "Rule",
    "RuleConfigError",
    "RuleContext",
    "RuleResult",
    "Severity",
    "Stage",
    "__version__",
]
