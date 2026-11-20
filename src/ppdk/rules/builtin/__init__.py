"""The rules shipped with the kit, by the name they are configured under (`ppdk.<name>`)."""

from .base_branch_rule import BaseBranchRule
from .command_rule import CommandRule
from .conflict_marker_rule import ConflictMarkerRule
from .env_file_rule import EnvFileRule
from .file_size_rule import FileSizeRule
from .secret_rule import SecretRule

# The prefix is added by the rule loader: project.toml says `rule = "ppdk.secret"`.
BUILTIN_RULES = {
    "base_branch": BaseBranchRule,
    "command": CommandRule,
    "conflict_marker": ConflictMarkerRule,
    "env_file": EnvFileRule,
    "file_size": FileSizeRule,
    "secret": SecretRule,
}

__all__ = [
    "BUILTIN_RULES",
    "BaseBranchRule",
    "CommandRule",
    "ConflictMarkerRule",
    "EnvFileRule",
    "FileSizeRule",
    "SecretRule",
]
