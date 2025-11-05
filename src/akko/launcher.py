"""Launcher module for AKKO application."""

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from akko.settings import ensure_config_file, get_settings, logger

TRUSTED_STREAMLIT_ARGS = ("-m", "streamlit", "run")


def gracefully_exit(message: str) -> None:
    """Log an error message and exit the application."""
    logger.error(message)
    sys.exit(1)


def _ensure_trusted_command(command: Sequence[str], app_path: Path) -> None:
    """Ensure the Streamlit launch command contains only trusted arguments."""
    if len(command) != 5:
        raise ValueError("Unexpected Streamlit command length.")
    if command[0] != sys.executable:
        raise ValueError("Unexpected interpreter for Streamlit launch.")
    if tuple(command[1:4]) != TRUSTED_STREAMLIT_ARGS:
        raise ValueError("Unexpected Streamlit CLI arguments.")
    if command[4] != str(app_path):
        raise ValueError("Unexpected app path in Streamlit command.")
    if any("\n" in part or "\r" in part for part in command):
        raise ValueError("Command contains disallowed control characters.")


def _build_streamlit_command(app_path: Path) -> list[str]:
    """Build and validate the command used to start Streamlit."""
    command = [sys.executable, *TRUSTED_STREAMLIT_ARGS, str(app_path)]
    _ensure_trusted_command(command, app_path)
    return command


def launch() -> None:
    """Launch the AKKO Streamlit application."""
    launch_cwd = Path.cwd()
    ensure_config_file(start_dir=launch_cwd)
    package_path = get_settings().package_path
    app_path = (package_path / "front" / "app.py").resolve()

    if not app_path.is_file() or package_path not in app_path.parents:
        gracefully_exit("Streamlit entrypoint not found in trusted location.")

    command: list[str]
    try:
        command = _build_streamlit_command(app_path)
    except ValueError as exc:
        gracefully_exit(str(exc))
        return

    try:
        env = os.environ.copy()
        env["AKKO_WORKDIR"] = str(launch_cwd)
        # Launch Streamlit from the app directory
        subprocess.run(  # noqa: S603 - command is built from trusted inputs only
            command,
            check=True,
            cwd=str(launch_cwd),
            env=env,
        )

    except FileNotFoundError as e:
        gracefully_exit(e.__repr__())
    except Exception as e:
        gracefully_exit(f"Error launching AKKO: {e}")


if __name__ == "__main__":
    launch()
