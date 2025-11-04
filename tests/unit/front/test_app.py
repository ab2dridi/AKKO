from __future__ import annotations

import importlib
import sys
from datetime import datetime, timedelta
from types import ModuleType, SimpleNamespace

import pytest
from pytest_mock import MockerFixture


def _load_app_module(
    mocker: MockerFixture, session_state: dict[str, object]
) -> ModuleType:
    sidebar_stub = SimpleNamespace(
        markdown=mocker.Mock(),
        header=mocker.Mock(),
        radio=mocker.Mock(return_value="🔗 Links"),
    )

    mocker.patch("streamlit.set_page_config")
    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.caption")
    mocker.patch("streamlit.warning")
    mocker.patch("streamlit.success")
    mocker.patch("streamlit.error")
    mocker.patch("streamlit.info")
    mocker.patch("streamlit.rerun")
    mocker.patch("streamlit.button", return_value=False)
    mocker.patch("streamlit.text_input", return_value="")
    mocker.patch("streamlit.stop")
    mocker.patch("streamlit.session_state", session_state)
    mocker.patch("streamlit.sidebar", sidebar_stub)
    mocker.patch("akko.front.links_page.show_links")
    mocker.patch("akko.core.security.load_links", return_value=[])

    sys.modules.pop("akko.front.app", None)
    return importlib.import_module("akko.front.app")


@pytest.mark.usefixtures("reset_logger_state")
@pytest.mark.usefixtures("reset_settings_cache")
def test_check_auto_lock_unlocks_when_inactive(mocker: MockerFixture) -> None:
    session_state: dict[str, object] = {
        "authenticated": True,
        "last_activity": datetime.now(),
        "fernet": object(),
    }

    app = _load_app_module(mocker, session_state)
    session_state["last_activity"] = datetime.now() - timedelta(
        minutes=app.AUTO_LOCK_MINUTES + 1
    )
    warning = mocker.patch("akko.front.app.st.warning")
    rerun = mocker.patch("akko.front.app.st.rerun")

    app.check_auto_lock()

    assert session_state["authenticated"] is False
    assert "fernet" not in session_state
    warning.assert_called_once()
    rerun.assert_called_once()


@pytest.mark.usefixtures("reset_logger_state")
@pytest.mark.usefixtures("reset_settings_cache")
def test_check_auto_lock_keeps_state_when_recent(mocker: MockerFixture) -> None:
    session_state: dict[str, object] = {
        "authenticated": True,
        "last_activity": datetime.now(),
        "fernet": object(),
    }

    app = _load_app_module(mocker, session_state)
    warning = mocker.patch("akko.front.app.st.warning")
    rerun = mocker.patch("akko.front.app.st.rerun")

    app.check_auto_lock()

    assert session_state["authenticated"] is True
    assert session_state["fernet"] is not None
    warning.assert_not_called()
    rerun.assert_not_called()


@pytest.mark.usefixtures("reset_logger_state")
@pytest.mark.usefixtures("reset_settings_cache")
def test_update_activity_sets_last_activity_timestamp(
    mocker: MockerFixture,
) -> None:
    fake_now = datetime(2024, 1, 1, 12, 0, 0)
    session_state: dict[str, object] = {
        "authenticated": True,
        "last_activity": datetime.now(),
        "fernet": None,
    }

    app = _load_app_module(mocker, session_state)
    datetime_mock = mocker.Mock()
    datetime_mock.now.return_value = fake_now
    mocker.patch("akko.front.app.datetime", datetime_mock)
    mocker.patch("akko.front.app.st.session_state", session_state)

    app.update_activity()

    assert session_state["last_activity"] == fake_now
    datetime_mock.now.assert_called_once()
