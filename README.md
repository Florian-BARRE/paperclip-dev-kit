# paperclip-dev-kit (ppdk)

Light git guardrails for coding agents. `ppdk` is installed **once** on the machine where agents work;
each repository only carries a `.ppdk/` folder that says which rules run at each stage:

- **commit** (git `pre-commit` hook): fast checks on the staged files;
- **push** (git `pre-push` hook): the complete checks on what the branch changed;
- **ci** (a GitHub workflow): the same checks on every pull request.

A failing rule refuses the commit or push, and the agent gets a report saying which rule failed, in
which file and line, and what to do.

```
.ppdk/
├── project.toml        # which rules run at each stage, with their options
└── rules/              # the repository's own rules, one Python file per rule
    └── structure_check.py
```

## Install

```bash
uv tool install git+https://github.com/Florian-BARRE/paperclip-dev-kit   # once per machine
```

Then make git call it for every repository (a repository without `.ppdk/` is left alone):

```bash
mkdir -p /usr/local/share/ppdk/hooks
for hook in pre-commit pre-push; do
  printf '#!/bin/sh\nexec ppdk hook %s\n' "$hook" >/usr/local/share/ppdk/hooks/$hook
  chmod +x /usr/local/share/ppdk/hooks/$hook
done
git config --system core.hooksPath /usr/local/share/ppdk/hooks
```

In CI, copy [`templates/ci.yml`](templates/ci.yml) to `.github/workflows/ppdk.yml`.

## Use

```bash
ppdk init              # create .ppdk/project.toml and an example rule
ppdk validate          # check the configuration and load every rule
ppdk check commit      # run a stage by hand (commit, push or ci)
```

Exit codes: `0` passed, `1` refused (a rule blocks), `2` the kit could not run (bad configuration).

## Configure

```toml
[project]
base = "main"      # the branch work merges into
timeout = 900      # default seconds for ppdk.command

[[on.commit]]
rule = "ppdk.secret"                  # a built-in rule

[[on.commit]]
rule = "rules.structure_check"        # .ppdk/rules/structure_check.py
paths = ["src/**"]                    # runs only when these files change, sees only them
severity = "warn"                     # reports without blocking (default: "error")

[[on.push]]
rule = "ppdk.command"
command = ["uv", "run", "pytest"]
```

Built-in rules: `ppdk.base_branch`, `ppdk.env_file`, `ppdk.secret`, `ppdk.conflict_marker`,
`ppdk.file_size`, `ppdk.command`. Details: [docs/configuration.md](docs/configuration.md).

## Write a rule

```python
# .ppdk/rules/no_print.py
from ppdk import Finding, Rule, RuleContext, RuleResult


class NoPrintRule(Rule):
    """Refuses debugging prints in Python files."""

    def run(self, context: RuleContext) -> RuleResult:
        findings = []
        for path in context.changed_files:
            text = context.read_text(path)
            if path.endswith(".py") and text:
                for number, line in enumerate(text.splitlines(), start=1):
                    if line.strip().startswith("print("):
                        findings.append(Finding("use the logger", path, number))
        return RuleResult(findings=tuple(findings))
```

The kit finds the single `Rule` subclass of the file, runs it, and turns any exception into a clear
"BROKEN" line instead of crashing the hook. Details: [docs/writing-a-rule.md](docs/writing-a-rule.md).

## Develop

```bash
uv sync
uv run pytest
uv run ruff check src tests && uv run ruff format --check src tests
```
