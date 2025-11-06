# Contributing to AKKO

Thanks for your interest in **AKKO**! This guide explains how to set up a local environment, follow our coding conventions, run tests and type-checkers, and submit changes. It also includes an **alternative workflow using `uv`** in addition to the classic `venv + pip` setup.

## Table of contents

* [Getting started](#getting-started)
* [Local development](#local-development)
* [Code guidelines](#code-guidelines)
* [Testing & coverage](#testing--coverage)
* [Static typing](#static-typing)
* [Running the app](#running-the-app)
* [Submitting changes](#submitting-changes)
* [Architecture notes (high-level)](#architecture-notes-high-level)
* [Security & data](#security--data)
* [Release & versioning](#release--versioning)

---

## Getting started

1. **Clone**

```bash
git clone https://github.com/your-repo/akko.git
cd akko
```

2. **Python version**
   Use **Python 3.10+** (3.10 or newer).

3. **Choose your environment setup**
   We support two equivalent flows. Pick one:

### A. Classic: `venv` + `pip`

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install -U pip
pip install -r requirements.txt
```

### B. Fast alternative: `uv` (recommended for speed & reproducibility)

`uv` is a fast Python package/dependency manager.

* Install `uv` (one-time): [https://docs.astral.sh/uv/getting-started/](https://docs.astral.sh/uv/getting-started/)
* Create and sync environment:

```bash
# Create a local virtual env at .venv and sync from requirements.txt
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

# Sync exactly the dependencies from requirements files
uv pip sync requirements.txt
# (optional) for dev extras if defined via requirements-dev.in/out
# uv pip sync requirements.txt requirements-dev.txt
```

> **Tip:** With `uv`, you can also run commands without manual activation:
>
> ```bash
> uv run -m pytest
> uv run mypy .
> uv run streamlit run src/akko/front/app.py
> ```

---

## Local development

* **Source layout:** application code lives under `src/akko`.
* **Entrypoint:** an app launcher is exposed at `akko.launcher:launch` (also available as the `akko-launch` console script if installed).
* **Configuration:** on first run, AKKO creates a working directory and a default `akko-config.json` if missing.

---

## Code guidelines

* **Typing:** favor explicit, strict typing across the codebase (`Literal`, `TypedDict` when appropriate). Pydantic **v2** models only; use `model_validate`, `model_dump` and v2-style validators.
* **Serialization:** prefer **orjson** for JSON IO/performance.
* **Logging:** use **structlog**; avoid `print`. Stick to structured, readable logs.
* **UI (Streamlit):** reuse shared UI helpers (e.g. `copy_button`) for consistent behavior across browsers.
* **Style:** small, focused functions; remove dead code; document important design decisions in your PR description.
* **Install pre-commit:** use pre-commit to ensure linting, type safety,...

**Improvement checklist to consider in PRs** (continuous improvements):

1. Factor common Streamlit patterns/components and consolidate CSS.
2. Expand UI-related tests by extracting testable pure logic.
3. Add `pre-commit` hooks (format, lint, typos) for a smooth DX.
4. Adopt **Conventional Commits** to enable automated changelogs.
5. Document a short guide: *“How to add a new credential type”*.

---

## Testing & coverage

We use **pytest** with coverage.

```bash
# Classic
pytest

# Or with uv (no manual activation needed)
uv run -m pytest
```

A terminal summary and an **HTML coverage report** are generated:

* Terminal shows per-file coverage (missing lines summarized).
* HTML report in `./htmlcov/index.html`.

> If your IDE picks up coverage automatically, point it to `htmlcov`.

---

## Static typing

* **mypy** (strict, with Pydantic v2 plugin):

```bash
mypy .
# Or: uv run mypy .
```


---

## Running the app

Two convenient ways:

1. **Via the launcher (recommended)**

```bash
# Classic
python -m akko.launcher
# Or after package install:
akko-launch

# With uv
uv run akko-launch
```

The launcher sets up paths and invokes `streamlit run` with the right entry file.

2. **Direct Streamlit** (advanced/dev)

```bash
# Classic
streamlit run src/akko/front/app.py

# With uv
uv run streamlit run src/akko/front/app.py
```

Prefer the launcher to avoid path/config surprises.

---

## Submitting changes

1. **Create a branch**

```bash
git checkout -b feat/concise-summary  # or fix/... chore/...
```

2. **Commits**

* Write clear messages; **Conventional Commits** welcome (`feat:`, `fix:`, `docs:`, ...).
* **Never ever** commit secrets/tokens/internal URLs.
* Run formatters/linters locally (e.g., `ruff`) and **pre-commit** hooks.

3. **Pre-PR checklist**

```bash
pytest
mypy .
# optional
pyright
```

Ensure tests pass and coverage is stable.

4. **Open a Pull Request**

* Explain **context**, **changes**, and **impact** (user & dev).
* Add screenshots/gifs when UI changes.
* Reference any of the improvement items you addressed (see checklist above).

---

## Architecture notes (high-level)

* **Data & encryption:**

  * Key derivation → symmetric encryption (Fernet) for local secret storage.
  * Persistence with `orjson`; redact/`SecretStr` before dumps.
  * Utility helpers centralize `derive_key`, `load_data`, `save_data`.

* **Credentials (extensible):**

  * Registry of Pydantic models via a decorator (e.g., `@register_credential("...")`).
  * Typed usage (`CredentialUnion`) and normalized names/factories for creation.
  * See `src/akko/typing/credentials.py` for adding new types.

* **Links (public/private):**

  * Models: `LinkEntry`, `LinkCollection`, `ApplicationData` (Pydantic v2).
  * Separate JSON stores; merged categories in the UI for filtering.
  * UI allows add/remove, filtering, copy, icon helpers.

* **Settings:**

  * Pydantic settings (`AkkoSettings`) + automatic `akko-config.json` generation.
  * Data dirs are created on demand; paths resolved from the config file.

* **Logging:**

  * `structlog` configured early; human-readable console by default; optional JSON file handler.

---

## Security & data

* **Never commit** secrets/passwords/tokens.
* Data files (encrypted stores or link JSONs) live under the configured `data/...` directory and are created if missing.
* Make sure logs **don’t leak sensitive information**.

---

## Release & versioning

* Prefer **Semantic Versioning** (`MAJOR.MINOR.PATCH`).
* Packaging is handled by Hatch; adjust targets if you plan to publish wheels.

---

## Quick commands cheat-sheet

**Setup**

```bash
# Classic
python -m venv .venv && source .venv/bin/activate && pip install -U pip && pip install -r requirements.txt
# uv
uv venv .venv && source .venv/bin/activate && uv pip sync requirements.txt
```

**Run**

```bash
python -m akko.launcher
# or
uv run akko-launch
```

**Test & type-check**

```bash
pytest && mypy .
# or
uv run -m pytest && uv run mypy .
```

**Streamlit directly**

```bash
streamlit run src/akko/front/app.py
# or
uv run streamlit run src/akko/front/app.py
```

**Pre-commit (optional but encouraged)**

```bash
pip install pre-commit  # or: uv pip install pre-commit
pre-commit install # or: uv run pre-commit install
pre-commit run --all-files # or: uv run pre-commit run --all-files
```

Thanks for contributing to **AKKO** 💚
