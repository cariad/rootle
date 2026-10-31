# CLAUDE.md

rootle is a Python package with functions for interacting with the file systems. Each function lives in a module of its own with the same name (`src/rootle/<name>.py`) and is re-exported from `rootle`. Helpers for testing code that uses the file system live in `rootle.testing` the same way (`src/rootle/testing/<name>.py`). Types that functions return live in `rootle.types`, each in a module named after it in lowercase (`src/rootle/types/identity.py` for `Identity`). Windows error codes live in `rootle.winerror` (`src/rootle/winerror.py`), like Python's `errno`, documented on one page, `docs/winerror.md`.

## Commands

```bash
mise install                # Install the pinned tools
mise run lint               # Every linter, stopping at the first failure
mise run lint:editorconfig  # One linter
mise run test               # The tests, with 100% branch coverage required
mise run docs:build         # Build the documentation site to site/
mise run docs:serve         # Serve the documentation site locally
mise exec -- rumdl fmt      # Fix Markdown
mise exec -- tombi format . # Fix TOML formatting
mise exec -- uv run --locked ruff check --fix  # Fix what ruff can
mise exec -- uv run --locked ruff format       # Format Python
```

## Keep in sync

- `.config/mise.toml`•`min_version` ↔ the mise-action `version` in every job that installs mise, in `.github/workflows/ci.yml` and `.github/workflows/release.yml`.
- After changing `.config/mise.toml`•`tools`, run `mise lock`, because CI sets `MISE_LOCKED=1`.
- Every `lint:*` task in `.config/mise.toml` ↔ a step of its own in `.github/workflows/ci.yml`'s `lint` job.
- Every function exported from `rootle` ↔ its own page `docs/functions/<name>.md` and its entry under "Functions" in `zensical.toml`•`project`•`nav`. Likewise for `rootle.testing`, with `docs/testing/<name>.md` and "Testing", and for `rootle.types`, with `docs/types/<module>.md` and "Types". `tests/test_docs.py` checks both, for every module in its `SECTIONS`.
- `.config/mise.toml`•`tools`•`uv` ↔ `pyproject.toml`•`tool.uv`•`required-version`, which it must satisfy. The range's floor must never be above the uv that Dependabot's uv updater bundles (0.12.19 on 2026-10-18), or every one of Dependabot's uv updates fails.
- `pyproject.toml`•`project`•`requires-python` ↔ `pyproject.toml`•`tool.pyright`•`pythonVersion` ↔ `.python-version`.

## Conventions

- The README is in the maintainer's own voice. Change only what a task needs, and ask before rewriting their wording.
- Never run `mise trust`. If mise says a file isn't trusted, ask.
- British spelling.
- Within a Python module, functions are in alphabetical order, with private (underscored) names first. So are a class's methods, where dunders count as underscored, so `__init__` comes after `__enter__` and `__exit__`.
- pyright is strict, so every name must be fully typed.
- When a function behaves differently between operating systems, its docstring describes each in a paragraph of its own, after the general description, starting with the operating systems in bold, like `**Linux & macOS:**` and `**Windows:**`.
- In tests, compute values into named variables (like `resolved` and `expect`) and leave a blank line before the `assert`s, rather than computing them in the `assert` itself.
- Tests don't branch on the operating system or environment to choose what to expect. Write a test per outcome instead, each skipped where it doesn't apply with `@mark.skipif` and a reason. A test that's skipped on an operating system ends with the ones it runs on, like `_on_posix` or `_on_windows`. When a pair of tests covers the same behaviour on POSIX and Windows, mark them `@posix_only` and `@windows_only` from `tests/marks.py` rather than giving each its own reason.
