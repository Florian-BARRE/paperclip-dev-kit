# paperclip-dev-kit: rules for coding agents

`ppdk` is a small Python CLI: git hooks and CI run the rules a repository declares in `.ppdk/`.

## Commands

- Install: `uv sync`
- Tests: `uv run pytest -q`
- Lint and format: `uv run ruff check src tests` and `uv run ruff format --check src tests`
- The kit checks itself: `uv run ppdk validate`, `uv run ppdk check commit`

## Map

```
src/ppdk/
├── __init__.py          public facade: what a repository rule imports (Rule, Finding, RuleContext...)
├── entrypoint.py        the `ppdk` command: arguments, logs, then PpdkApplication
├── application.py       the commands: check, hook, validate, init
├── scaffold.py          the files `ppdk init` writes
├── config/              .ppdk/project.toml -> ProjectConfig
├── git/                 read-only git access, file readers (index / revision)
├── rules/               the Rule contract, its value types, builtin/ rules
└── engine/              rule loader, context builder, stage runner, report
.ppdk/                   the kit's own rules (dogfooding)
templates/ci.yml         the workflow repositories copy
docs/                    French documentation (configuration, writing a rule)
```

## Conventions

- Follow the coding standards: classes, one responsibility per file, under 400 lines, Code Summary
  header, typed signatures, Google docstrings, loggerplusplus logs with START/END.
- Code, comments and commit messages in English; `docs/` in French.
- Commits: `type(scope): summary`.
- Never break the public facade (`ppdk/__init__.py`) without a major version: repository rules
  depend on it.
- A new built-in rule: one file in `rules/builtin/`, registered in `BUILTIN_RULES`, documented in
  `docs/configuration.md`, tested in `tests/test_builtin_rules.py`.
