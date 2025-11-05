from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import date

from pytest_mock import MockerFixture

from akko.front.credentials_manage import (
    _make_credential_form,
    _persist_credential,
    add_credential,
)
from akko.typing.credentials import CredentialUnion, WebsiteCredential


class _DummyForm(AbstractContextManager[None]):
    def __enter__(self) -> None:  # pragma: no cover - trivial context
        return None

    def __exit__(self, *args: object) -> None:  # pragma: no cover - trivial context
        return None


def test_persist_credential_appends_and_saves(mocker: MockerFixture) -> None:
    data: list[tuple[str, CredentialUnion]] = []
    credential = WebsiteCredential.model_validate(
        {
            "name": "Example",
            "url": "https://example.com",
            "username": "user",
            "password": "secret",  # pragma: allowlist secret
        }
    )
    save_mock = mocker.patch("akko.front.credentials_manage.save_data")

    fernet = mocker.Mock()
    _persist_credential(data, fernet, credential)

    assert data == [("🌐 Website", credential)]
    save_mock.assert_called_once_with(data, fernet)


def test_make_credential_form_validates_website(mocker: MockerFixture) -> None:
    responses = iter(["Example", "https://example.com", "user", "secret"])

    def _pop_response(*args: object, **kwargs: object) -> str:
        _ = args
        _ = kwargs
        return next(responses)

    mocker.patch("streamlit.text_input", side_effect=_pop_response)

    result = _make_credential_form("Website")

    assert bool(result["validation"]) is True
    assert result["name"] == "Example"


def test_make_credential_form_handles_gitlab_token(mocker: MockerFixture) -> None:
    responses = iter(["CI token", "ghp_secret"])

    def _pop_token(*args: object, **kwargs: object) -> str:
        _ = args
        _ = kwargs
        return next(responses)

    mocker.patch("streamlit.text_input", side_effect=_pop_token)
    mocker.patch("streamlit.checkbox", return_value=True)
    future_date = date.today().replace(year=date.today().year + 1)
    mocker.patch("streamlit.date_input", return_value=future_date)

    result = _make_credential_form("GitLab Token")

    assert result["validation"] is True
    assert result["expires"] is True
    assert result["expiration_date"] == future_date


def test_add_credential_successfully_persists(mocker: MockerFixture) -> None:
    mocker.patch("streamlit.subheader")
    mocker.patch("streamlit.radio", return_value="🌐 Website")
    mocker.patch("streamlit.form", return_value=_DummyForm())
    responses = iter(["Example", "https://example.com", "user", "secret"])

    def _pop_form_value(*args: object, **kwargs: object) -> str:
        _ = args
        _ = kwargs
        return next(responses)

    mocker.patch("streamlit.text_input", side_effect=_pop_form_value)
    mocker.patch("streamlit.form_submit_button", return_value=True)
    success_mock = mocker.patch("streamlit.success")
    error_mock = mocker.patch("streamlit.error")
    save_mock = mocker.patch("akko.front.credentials_manage.save_data")

    data: list[tuple[str, CredentialUnion]] = []
    add_credential(data, mocker.Mock())

    assert len(data) == 1
    save_mock.assert_called_once()
    success_mock.assert_called_once()
    error_mock.assert_not_called()


def test_add_credential_reports_invalid_input(mocker: MockerFixture) -> None:
    mocker.patch("streamlit.subheader")
    mocker.patch("streamlit.radio", return_value="🌐 Website")
    mocker.patch("streamlit.form", return_value=_DummyForm())
    mocker.patch("streamlit.text_input", return_value="")
    mocker.patch("streamlit.form_submit_button", return_value=True)
    error_mock = mocker.patch("streamlit.error")
    save_mock = mocker.patch("akko.front.credentials_manage.save_data")

    add_credential([], mocker.Mock())

    error_mock.assert_called_once()
    save_mock.assert_not_called()
