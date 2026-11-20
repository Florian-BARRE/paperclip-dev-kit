# ====== Code Summary ======
# Built-in rule ppdk.conflict_marker: refuses files that still contain git conflict markers.

# ====== Standard Library Imports ======
from __future__ import annotations

import re
from typing import Final

# ====== Local Project Imports ======
from .file_content_rule import FileContentRule

# ====== Constants ======
# `=======` alone is left out on purpose: it is also a heading underline in Markdown and reST.
_MARKER: Final[re.Pattern[str]] = re.compile(r"^(<{7}|>{7})( |$)")


class ConflictMarkerRule(FileContentRule):
    """Refuses a line that starts a `<<<<<<<` or `>>>>>>>` conflict marker."""

    # =======================
    #   Private Methods
    # =======================
    def _check_line(self, line: str) -> str | None:
        """Return a reason when `line` is a conflict marker."""
        if _MARKER.match(line):
            return "unresolved merge conflict marker: resolve the conflict, then commit again"
        return None
