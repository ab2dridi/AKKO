# 🛡️ AKKO

**AKKO** (Access Key Keep Ownership) is a **simple, secure, and serverless** password and credential manager designed to keep your data under your control. Built with [Streamlit](https://streamlit.io/), it focuses on **simplicity**, **privacy**, and **data sovereignty**. AKKO now targets **Python 3.10+**.

---

## ✨ Main Features

- Clean and intuitive interface without clutter
- Local encryption with `cryptography.Fernet`
- Smart search, filtering, and quick link/token management
- 100% offline: no external servers or databases
- Auto-lock after inactivity for extra security
- Typed configuration powered by `pydantic-settings`

---

## ⚙️ Requirements

- Python 3.10 or newer available on your PATH
- A modern browser compatible with Streamlit
- Optional tooling: [uv](https://docs.astral.sh/uv/) for ultra-fast installs, [pipx](https://pipx.pypa.io/) for isolated CLI usage

---

## � Quick Launch with `akko-launch`

`akko-launch` is the packaged command-line entry point that validates and starts the Streamlit UI from a trusted location.

### with uv

```bash
# Install the local package, then launch it with uv run
uv pip install .
uv run akko-launch
```

### with pipx

```bash
# Install AKKO with pipx, then launch the interface
pipx install .
akko-launch
```

### with plain virtual environement

```bash
python -m venv .venv-akko
source .venv-akko/bin/activate        # macOS/Linux
# .venv-akko\Scripts\activate         # Windows PowerShell
pip install .
akko-launch
```

Prefer a manual fallback? You can always execute `python -m akko.launcher` from an environment where AKKO is installed.

---

## 📦 Local Installation

### Classic virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # On macOS/Linux
# .venv\Scripts\activate         # On Windows PowerShell
pip install --upgrade pip
pip install -r requirements.txt
akko-launch
```

### uv workflow

```bash
uv sync                          # Reads pyproject.toml and requirements.txt
uv run akko-launch               # Launch the UI inside the managed environment
```

Add development tooling with `uv sync --extra dev` or install optional dependencies via `pip install .[dev]`.

---

## 📦 Dependency Management

**Runtime (`requirements.txt`)**

```text
cryptography>=43.0.0
orjson>=3.9.1
pydantic-settings>=2.3.0
pydantic>=2.7.0
streamlit>=1.38.0
structlog>=23.1.0
```

Install these with `pip install -r requirements.txt` or `uv pip install -r requirements.txt`. Update the file whenever a runtime dependency changes to keep packaging metadata in sync.

**Development (`requirements-dev.in`)**

`requirements-dev.in` is the curated list of tooling used during development (formatters, linters, docs, testing, packaging). Hatch's `requirements_txt` metadata hook exposes it as the `[dev]` optional dependency set. Add new tools here, then install them with one of the following:

- `uv pip install -r requirements-dev.in`
- `uv sync --extra dev`
- `pip install .[dev]`

This keeps the shipped runtime minimal while letting contributors bootstrap a full workstation in one command.

---

## 🧰 Useful Files

| Path                                     | Description                                                              |
| ---------------------------------------- | ------------------------------------------------------------------------ |
| `src/akko/launcher.py`                   | Implements the `akko-launch` CLI and guards the Streamlit invocation.    |
| `src/akko/front/app.py`                  | Main Streamlit application rendered in the browser.                      |
| `src/akko/core/security.py`              | Encryption, hashing, and credential safety helpers.                      |
| `src/akko/settings.py`                   | Loads and validates configuration from `config.json`.                    |
| `src/akko/resources/default-config.json` | Template copied whenever `config.json` is missing.                       |
| `config.json`                            | Project-level configuration generated on first launch.                   |
| `data/encrypted/`                        | Encrypted credentials vault (contains `credentials.enc`).                |
| `data/private/`                          | Private link definitions (`private_links.json`).                         |
| `data/public/`                           | Public/shared links (`public_links.json`) and related assets.            |

---

## 💾 Data & Configuration

### Storage layout

```text
AKKO/
 └── data/
   ├── encrypted/
   │    └── credentials.enc        → encrypted credentials (passwords, tokens, SSH keys)
   ├── private/
   │    └── private_links.json     → private or internal links (stored in clear text)
   └── public/
     └── public_links.json      → public or shareable resources (plain JSON)
```

The exact locations are controlled by `config.json`, so you can relocate the vault by editing the corresponding paths.

### Configuration file

- At startup, `akko.settings.ensure_config_file()` looks for `config.json` in the current directory or its parents.
- If none is found, the default template from `src/akko/resources/default-config.json` is copied next to the launcher.
- Configuration fields are validated with `pydantic-settings`; invalid values lead to a descriptive error.

Example excerpt:

```json
{
  "data_paths": {
    "credentials": "data/encrypted/credentials.enc",
    "private_links": "data/private/private_links.json",
    "public_links": "data/public/public_links.json"
  },
  "security": {
    "auto_lock_minutes": 5,
    "hash_check": true
  }
}
```

Relative paths are resolved from the directory that contains `config.json`. Edit the file to customize storage locations, feature flags, or theme options. Restart the app (or rerun `akko-launch`) after making changes.

### Security model

- **Credentials** are the only data encrypted on disk, stored in `credentials.enc` using your master password and `cryptography.Fernet`.
- **Private links** stay in clear text but remain local to your machine.
- **Public links** and icons are plain JSON/static assets that can be shared safely.
- No standalone encryption key is stored anywhere — the key is derived from your master password at runtime.

### Master password

On the first launch, AKKO prompts you to create a **master password**. It:

- encrypts and decrypts your credentials,
- is never stored or transmitted,
- cannot be recovered by the application.

Lose the password and the encrypted data becomes unreachable.

### Moving or backing up data

1. Copy your `config.json` and the entire `data/` directory.
2. Paste them into the same locations on the new machine.
3. Launch AKKO and provide the same master password.

`data/public/` can be copied or versioned freely.

### Important notes

- Keep `data/encrypted/credentials.enc` out of commits to avoid leaking secrets.
- Keep a secure backup of `credentials.enc` if you rely on AKKO for mission-critical data.
- Delete the `data/` directory to start fresh; AKKO will recreate the structure on the next launch.

---

## 🧯 Troubleshooting

- `akko-launch: command not found` → Install the package locally (`pip install -r requirements.txt`) or run it via `uv tool run akko-launch`.
- `Configuration validation failed` → Review `config.json`; ensure field names and value types match the template.
- `Streamlit entrypoint not found in trusted location` → The package layout differs from expectations; reinstall AKKO or avoid moving files out of `src/akko/front/`.
- `Port already in use` → Pick another port by running `STREAMLIT_SERVER_PORT=8502 akko-launch` (or restart the conflicting session).
- `ModuleNotFoundError: cryptography` → Reinstall dependencies with `pip install -r requirements.txt` or `uv sync`.
- `Python 3.9 detected` → Upgrade your interpreter to Python 3.10+ before launching.

---

## 🔒 Security

- Data is **encrypted locally** before saving.
- The encryption key is derived from your master password (never stored in plain text).
- Auto-lock prevents unauthorized access after inactivity.

> AKKO collects **no data**, locally or remotely.

---

## 🌐 Philosophy

> **"Keep it simple. Keep it yours."**

AKKO is built on one belief:  
your secrets should belong to **you**, not to some third-party service.  
No cloud, no tracking, no nonsense — just your vault and your control.

---

## 📸 Screenshots

### 🔐 First Authentication

![First Authentication](docs/first_auth.png)

### ➕ Add Credentials

![Add Credentials](docs/add_credentials.png)

### 📂 View Stored Credentials

![Show Credentials](docs/show_credentials.png)

### 🌐 Add a Link

![Add Link](docs/add_link.png)

### 🔗 View Links

![Show Links](docs/show_links.png)

---

## 🧠 Author

Created with ❤️, caffeine, and mild frustration at closed systems.  
Developed by **ab2dridi**.  
Licensed under MIT — use it, improve it, and keep your freedom.
