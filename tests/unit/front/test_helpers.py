from __future__ import annotations

from pathlib import Path

from pytest_mock import MockerFixture

import akko.front.helpers as helpers


def test_try_copy_success_triggers_toast(mocker: MockerFixture) -> None:
    copy_mock = mocker.patch("akko.front.helpers.pyperclip.copy")
    html_mock = mocker.patch("akko.front.helpers.st_html")
    toast_mock = mocker.patch("akko.front.helpers.st.toast")
    warning_mock = mocker.patch("akko.front.helpers.st.warning")

    helpers.try_copy("value", "Label")

    copy_mock.assert_called_once_with("value")
    html_mock.assert_called_once()
    toast_mock.assert_called_once_with("Label copié dans le presse-papiers.")
    warning_mock.assert_not_called()


def test_try_copy_failure_falls_back_to_client_copy(mocker: MockerFixture) -> None:
    mocker.patch("akko.front.helpers.pyperclip.copy", side_effect=RuntimeError("boom"))
    html_mock = mocker.patch("akko.front.helpers.st_html")
    toast_mock = mocker.patch("akko.front.helpers.st.toast")
    warning_mock = mocker.patch("akko.front.helpers.st.warning")

    helpers.try_copy("value", "Label")

    # JS fallback used → toast shown, no warning
    html_mock.assert_called_once()
    toast_mock.assert_called_once_with("Label copié dans le presse-papiers.")
    warning_mock.assert_not_called()


def test_find_icon_returns_matching_file(tmp_path: Path, mocker: MockerFixture) -> None:
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    (icons_dir / "finance.png").write_text("", encoding="utf-8")
    (icons_dir / "other.txt").write_text("", encoding="utf-8")

    settings_stub = type("Settings", (), {"icons_directory": icons_dir})
    mocker.patch("akko.front.helpers.get_settings", return_value=settings_stub)

    icon_path = helpers.find_icon("Finance")

    assert icon_path == icons_dir / "finance.png"


def test_find_icon_returns_none_when_missing(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    settings_stub = type("Settings", (), {"icons_directory": icons_dir})
    mocker.patch("akko.front.helpers.get_settings", return_value=settings_stub)

    assert helpers.find_icon("Unknown") is None


def test_find_icon_returns_none_when_directory_absent(mocker: MockerFixture) -> None:
    settings_stub = type("Settings", (), {"icons_directory": Path("/nonexistent")})
    mocker.patch("akko.front.helpers.get_settings", return_value=settings_stub)

    assert helpers.find_icon("Anything") is None
