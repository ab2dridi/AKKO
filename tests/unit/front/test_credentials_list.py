from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta
from typing import Any, cast

import pytest
from pytest_mock import MockerFixture

from akko.front.credentials_list import (
    _credential_icon,
    _filter_credentials,
    _render_credential_card,
    _render_delete_action,
    _render_search_box,
    _render_token_status,
    _render_type_filter,
    _render_website_credentials,
    show_credentials,
)
from akko.typing.credentials import CredentialPayload, WebsiteCredential


def test_render_search_box_normalizes_input(mocker: MockerFixture) -> None:
    mocker.patch("streamlit.text_input", return_value="  Foo  ")

    assert _render_search_box() == "foo"


def test_render_type_filter_returns_normalized_name(mocker: MockerFixture) -> None:
    mocker.patch("streamlit.markdown")
    mocker.patch("streamlit.radio", return_value="🌐 Website")

    assert _render_type_filter() == "Website"


def _make_sample_credentials() -> list[CredentialPayload]:
    website = WebsiteCredential.model_validate(
        {
            "name": "Portal",
            "url": "https://portal.example.com",
            "username": "alice",
            "password": "secret",  # pragma: allowlist secret
        }
    )
    return [("🌐 Website", website)]


def test_filter_credentials_applies_query_and_type() -> None:
    data = _make_sample_credentials()

    filtered = _filter_credentials(data, query="portal", selected_type="Website")

    assert filtered == data


@pytest.mark.parametrize(
    "case",
    [
        {"expires": False, "expiration": None, "expected": "info"},
        {"expires": True, "expiration": "not-a-date", "expected": "error"},
        {
            "expires": True,
            "expiration": (datetime.now() - timedelta(days=2)).isoformat(),
            "expected": "error",
        },
        {
            "expires": True,
            "expiration": (datetime.now() + timedelta(days=2)).isoformat(),
            "expected": "warning",
        },
        {
            "expires": True,
            "expiration": (datetime.now() + timedelta(days=30)).isoformat(),
            "expected": "success",
        },
    ],
)
def test_render_token_status_reports_state(
    mocker: MockerFixture,
    case: dict[str, object],
) -> None:
    info_mock = mocker.patch("streamlit.info")
    error_mock = mocker.patch("streamlit.error")
    warn_mock = mocker.patch("streamlit.warning")
    success_mock = mocker.patch("streamlit.success")

    _render_token_status(
        expires=cast(bool, case["expires"]),
        expiration_date=cast(str | None, case["expiration"]),
    )

    called = {
        "info": info_mock.called,
        "error": error_mock.called,
        "warning": warn_mock.called,
        "success": success_mock.called,
    }
    assert called[cast(str, case["expected"])] is True


def test_render_delete_action_removes_entry(mocker: MockerFixture) -> None:
    data = _make_sample_credentials()
    button_mock = mocker.patch("streamlit.button", return_value=True)
    save_mock = mocker.patch("akko.front.credentials_list.save_data")
    success_mock = mocker.patch("streamlit.success")
    rerun_mock = mocker.patch("streamlit.rerun")

    class _DummyColumn:
        def __enter__(self) -> _DummyColumn:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    column = cast(Any, _DummyColumn())

    _render_delete_action(column, 0, data, data[0], mocker.Mock())

    assert not data
    button_mock.assert_called_once()
    save_mock.assert_called_once()
    success_mock.assert_called_once()
    rerun_mock.assert_called_once()


def test_render_credential_card_invokes_renderer(mocker: MockerFixture) -> None:
    columns = [mocker.Mock() for _ in range(4)]
    mocker.patch("streamlit.columns", return_value=columns)

    class _DummyExpander:
        def __enter__(self) -> None:
            return None

        def __exit__(self, *args: object) -> None:
            return None

    mocker.patch("streamlit.expander", return_value=_DummyExpander())
    renderer = mocker.Mock()
    mocker.patch.dict(
        "akko.front.credentials_list.CREDENTIAL_RENDERERS",
        {"Website": renderer},
    )
    mocker.patch("akko.front.credentials_list._render_delete_action")

    data = _make_sample_credentials()
    _render_credential_card(0, data[0], data, mocker.Mock())

    renderer.assert_called_once()


def test_render_website_credentials_populates_columns(mocker: MockerFixture) -> None:
    copy_mock = mocker.patch("akko.front.credentials_list._render_copy_button")
    write_mock = mocker.patch("akko.front.credentials_list.st.write")
    markdown_mock = mocker.patch("akko.front.credentials_list.st.markdown")
    code_mock = mocker.patch("akko.front.credentials_list.st.code")

    columns = [nullcontext() for _ in range(3)]

    _, credential_model = _make_sample_credentials()[0]
    typed_credential = cast(WebsiteCredential, credential_model)
    url = str(typed_credential.url)

    _render_website_credentials(cast(list[Any], columns), (_, typed_credential), 0)

    write_mock.assert_any_call("**URL:**")
    write_mock.assert_any_call("**Username:**")
    code_mock.assert_any_call(url, language="")
    code_mock.assert_any_call(typed_credential.username, language="")
    markdown_mock.assert_any_call(f"[🌐 Open link]({url})", unsafe_allow_html=True)
    copy_mock.assert_called()


def test_show_credentials_handles_empty_and_filtered(mocker: MockerFixture) -> None:
    subheader_mock = mocker.patch("streamlit.subheader")
    info_mock = mocker.patch("streamlit.info")

    show_credentials([], mocker.Mock())

    info_mock.assert_called_once()
    subheader_mock.assert_called_once()

    mocker.patch("streamlit.warning")
    mocker.patch(
        "akko.front.credentials_list._render_search_box",
        return_value="portal",
    )
    mocker.patch(
        "akko.front.credentials_list._render_type_filter",
        return_value="Website",
    )
    mocker.patch("akko.front.credentials_list._filter_credentials", return_value=[])

    data = _make_sample_credentials()
    show_credentials(data, mocker.Mock())

    mocker.patch(
        "akko.front.credentials_list._filter_credentials",
        return_value=_make_sample_credentials(),
    )
    inject_mock = mocker.patch("akko.front.credentials_list._inject_styles")
    render_mock = mocker.patch("akko.front.credentials_list._render_credential_card")

    show_credentials(_make_sample_credentials(), mocker.Mock())

    inject_mock.assert_called_once()
    render_mock.assert_called()


def test_credential_icon_defaults_to_lock() -> None:
    assert _credential_icon("Unknown") == "🔐"
