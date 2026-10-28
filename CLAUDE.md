# CLAUDE.md

rootle is a Python package with functions for interacting with the file systems. It has no functionality yet.

## Commands

```bash
mise install                # Install the pinned tools
mise run lint               # Every linter, stopping at the first failure
mise run lint:editorconfig  # One linter
mise exec -- rumdl fmt      # Fix Markdown
mise exec -- tombi format . # Fix TOML formatting
mise exec -- uv run --locked ruff check --fix  # Fix what ruff can
mise exec -- uv run --locked ruff format       # Format Python
```

## Keep in sync

- `.config/mise.toml`•`min_version` ↔ the mise-action `version` in every job that installs mise, in `.github/workflows/ci.yml`.
- After changing `.config/mise.toml`•`tools`, run `mise lock`, because CI sets `MISE_LOCKED=1`.
- Every `lint:*` task in `.config/mise.toml` ↔ a step of its own in `.github/workflows/ci.yml`'s `lint` job.
- `.config/mise.toml`•`tools`•`uv` ↔ `pyproject.toml`•`tool.uv`•`required-version`, which it must satisfy. The range's floor must never be above the uv that Dependabot's uv updater bundles (0.12.19 on 2026-10-18), or every one of Dependabot's uv updates fails.
- `pyproject.toml`•`project`•`requires-python` ↔ `pyproject.toml`•`tool.pyright`•`pythonVersion` ↔ `.python-version`.

## Conventions

- The README is in the maintainer's own voice. Change only what a task needs, and ask before rewriting their wording.
- Never run `mise trust`. If mise says a file isn't trusted, ask.
- British spelling.
- Within a Python module, functions are in alphabetical order, with private (underscored) names first. So are a class's methods, where dunders count as underscored, so `__init__` comes after `__enter__` and `__exit__`.
- pyright is strict, so every name must be fully typed.
