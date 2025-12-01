from __future__ import annotations

import importlib
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from pytest_mock import MockerFixture

from akko.typing.credentials import WebsiteCredential


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


def _prepare_settings_stub(tmp_path: Path) -> SimpleNamespace:
    resources_dir = tmp_path / "resources"
    resources_dir.mkdir()
    (resources_dir / "app.css").write_text("/* css */", encoding="utf-8")

    return SimpleNamespace(
        app_name="AKKO",
        package_path=tmp_path,
        security=SimpleNamespace(auto_lock_minutes=5),
    )


def test_unlock_flow_updates_session_state(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    settings_stub = _prepare_settings_stub(tmp_path)
    mocker.patch("akko.settings.get_settings", return_value=settings_stub)
    mocker.patch("akko.core.security.load_links", return_value=[])
    sample_credential = WebsiteCredential.model_validate(
        {
            "name": "Portal",
            "url": "https://portal.example.com",
            "username": "alice",
            "password": "secret",  # pragma: allowlist secret
        }
    )
    mocker.patch(
        "akko.core.security.load_data",
        return_value=[("Website", sample_credential)],
    )
    mocker.patch("akko.core.security.derive_key", return_value=b"key")
    fake_fernet = object()
    mocker.patch("cryptography.fernet.Fernet", return_value=fake_fernet)

    session_state: dict[str, object] = {}
    mocker.patch("streamlit.session_state", session_state)

    sidebar_stub = SimpleNamespace(
        markdown=mocker.Mock(),
        header=mocker.Mock(),
        radio=mocker.Mock(return_value="🔐 Credentials"),
    )
    mocker.patch("streamlit.sidebar", sidebar_stub)
    mocker.patch("streamlit.set_page_config")
    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.caption")
    mocker.patch("streamlit.warning")
    success_mock = mocker.patch("streamlit.success")
    mocker.patch("streamlit.error")
    mocker.patch("streamlit.info")
    mocker.patch("streamlit.button", return_value=True)
    mocker.patch("streamlit.text_input", return_value="super-secret")
    rerun_mock = mocker.patch("streamlit.rerun")
    mocker.patch("streamlit.stop")

    sys.modules.pop("akko.front.app", None)

    importlib.import_module("akko.front.app")

    assert session_state["authenticated"] is True
    assert session_state["fernet"] is fake_fernet
    assert "last_activity" in session_state
    success_mock.assert_called_once()
    rerun_mock.assert_called_once()


def test_credentials_page_calls_renderers_when_authenticated(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    settings_stub = _prepare_settings_stub(tmp_path)
    mocker.patch("akko.settings.get_settings", return_value=settings_stub)

    sidebar_stub = SimpleNamespace(
        markdown=mocker.Mock(),
        header=mocker.Mock(),
        radio=mocker.Mock(return_value="🔐 Credentials"),
    )
    mocker.patch("streamlit.sidebar", sidebar_stub)
    mocker.patch("streamlit.set_page_config")
    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.caption")
    mocker.patch("streamlit.warning")
    mocker.patch("streamlit.success")
    mocker.patch("streamlit.error")
    mocker.patch("streamlit.info")
    button_mock = mocker.patch("streamlit.button", return_value=True)
    mocker.patch("streamlit.text_input", return_value="")
    mocker.patch("streamlit.rerun")

    sample_credential = (
        "Website",
        WebsiteCredential.model_validate(
            {
                "name": "Example",
                "url": "https://example.com",
                "username": "user",
                "password": "secret",  # pragma: allowlist secret
            }
        ),
    )
    mocker.patch("akko.core.security.load_links", return_value=[])
    mocker.patch("akko.core.security.load_data", return_value=[sample_credential])

    add_credential_mock = mocker.patch("akko.front.credentials_manage.add_credential")
    show_credentials_mock = mocker.patch("akko.front.credentials_list.show_credentials")

    session_state: dict[str, object] = {
        "authenticated": True,
        "last_activity": datetime.now(),
        "fernet": object(),
        "show_form_creds": False,
    }
    mocker.patch("streamlit.session_state", session_state)

    sys.modules.pop("akko.front.app", None)
    module = importlib.import_module("akko.front.app")

    assert session_state["show_form_creds"] is True
    assert isinstance(session_state["last_activity"], datetime)
    add_credential_mock.assert_called_once()
    show_credentials_mock.assert_called_once()
    button_mock.assert_called_with("Toggle add credential form", type="primary")
    assert module.AUTO_LOCK_MINUTES == 5
