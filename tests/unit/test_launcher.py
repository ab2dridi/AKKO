from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

import akko.launcher as launcher


def test_gracefully_exit_logs_and_exits(mocker: MockerFixture) -> None:
    error_mock = mocker.patch.object(launcher.logger, "error")
    exit_mock = mocker.patch("akko.launcher.sys.exit")

    launcher.gracefully_exit("fatal error")

    error_mock.assert_called_once_with("fatal error")
    exit_mock.assert_called_once_with(1)


def test_ensure_trusted_command_accepts_expected_sequence() -> None:
    app_path = Path("front/app.py")
    command = [launcher.sys.executable, *launcher.TRUSTED_STREAMLIT_ARGS, str(app_path)]

    launcher._ensure_trusted_command(command, app_path)


@pytest.mark.parametrize(
    "command",
    [
        [launcher.sys.executable],
        ["python", *launcher.TRUSTED_STREAMLIT_ARGS, "path"],
        [launcher.sys.executable, "streamlit", "run", "path", "extra"],
        [launcher.sys.executable, *launcher.TRUSTED_STREAMLIT_ARGS, "wrong"],
        [launcher.sys.executable, *launcher.TRUSTED_STREAMLIT_ARGS, "bad\npath"],
    ],
)
def test_ensure_trusted_command_rejects_invalid_sequences(command: list[str]) -> None:
    with pytest.raises(ValueError, match="Unexpected"):
        launcher._ensure_trusted_command(command, Path("front/app.py"))


def test_build_streamlit_command_returns_valid_command(tmp_path: Path) -> None:
    app_path = tmp_path / "front" / "app.py"

    command = launcher._build_streamlit_command(app_path)

    assert command[0] == launcher.sys.executable
    assert tuple(command[1:4]) == launcher.TRUSTED_STREAMLIT_ARGS
    assert command[4] == str(app_path)


def test_launch_runs_streamlit_when_app_exists(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    package_dir = tmp_path / "akko"
    app_dir = package_dir / "front"
    app_dir.mkdir(parents=True)
    (app_dir / "app.py").write_text("print('hello')", encoding="utf-8")

    mocker.patch("akko.launcher.find_package_path", return_value=package_dir)
    build_mock = mocker.patch(
        "akko.launcher._build_streamlit_command",
        return_value=["cmd"],
    )
    run_mock = mocker.patch("akko.launcher.subprocess.run")
    exit_mock = mocker.patch("akko.launcher.gracefully_exit")

    launcher.launch()

    build_mock.assert_called_once()
    assert build_mock.call_args.args[0] == (package_dir / "front" / "app.py").resolve()
    run_mock.assert_called_once_with(["cmd"], check=True)
    exit_mock.assert_not_called()


def test_launch_exits_when_entrypoint_missing(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch("akko.launcher.find_package_path", return_value=tmp_path)
    exit_mock = mocker.patch("akko.launcher.gracefully_exit", side_effect=SystemExit)

    with pytest.raises(SystemExit):
        launcher.launch()

    exit_mock.assert_called_once_with(
        "Streamlit entrypoint not found in trusted location."
    )


def test_launch_exits_when_command_build_fails(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    package_dir = tmp_path / "akko"
    app_dir = package_dir / "front"
    app_dir.mkdir(parents=True)
    (app_dir / "app.py").write_text("print('hello')", encoding="utf-8")

    mocker.patch("akko.launcher.find_package_path", return_value=package_dir)
    mocker.patch(
        "akko.launcher._build_streamlit_command",
        side_effect=ValueError("bad command"),
    )
    exit_mock = mocker.patch("akko.launcher.gracefully_exit", side_effect=SystemExit)

    with pytest.raises(SystemExit):
        launcher.launch()

    exit_mock.assert_called_once_with("bad command")


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (FileNotFoundError("streamlit"), "FileNotFoundError"),
        (RuntimeError("boom"), "Error launching AKKO: boom"),
    ],
)
def test_launch_exits_when_subprocess_fails(
    tmp_path: Path,
    mocker: MockerFixture,
    raised: Exception,
    expected: str,
) -> None:
    package_dir = tmp_path / "akko"
    app_dir = package_dir / "front"
    app_dir.mkdir(parents=True)
    (app_dir / "app.py").write_text("print('hello')", encoding="utf-8")

    mocker.patch("akko.launcher.find_package_path", return_value=package_dir)
    mocker.patch("akko.launcher._build_streamlit_command", return_value=["cmd"])
    mocker.patch("akko.launcher.subprocess.run", side_effect=raised)
    exit_mock = mocker.patch("akko.launcher.gracefully_exit", side_effect=SystemExit)

    with pytest.raises(SystemExit):
        launcher.launch()

    assert exit_mock.call_count == 1
    assert expected in exit_mock.call_args.args[0]
