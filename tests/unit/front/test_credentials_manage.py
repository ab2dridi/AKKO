from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any, cast

import pytest
from cryptography.fernet import Fernet
from pytest_mock import MockerFixture

import akko.front.credentials_manage as credentials_manage
from akko.typing.credentials import CredentialUnion, WebsiteCredential


def _get_private(name: str) -> object:
    return getattr(credentials_manage, name)


def test_persist_credential_appends_and_saves(mocker: MockerFixture) -> None:
    data: list[tuple[str, CredentialUnion]] = []
    fernet = Fernet.generate_key()
    fernet_instance = Fernet(fernet)
    save_mock = mocker.patch("akko.front.credentials_manage.save_data")

    persist = cast(
        Callable[[list[tuple[str, CredentialUnion]], Fernet, CredentialUnion], None],
        _get_private("_persist_credential"),
    )

    credential = WebsiteCredential(
        name="Test Site",
        url="https://test.com",
        username="user",
        password="pass",  # noqa: S106 # pragma: allowlist secret
    )

    persist(data, fernet_instance, credential)

    assert len(data) == 1
    assert data[0][0] == "🌐 Website"
    assert data[0][1] == credential
    save_mock.assert_called_once_with(data, fernet_instance)


def test_make_credential_form_website(mocker: MockerFixture) -> None:
    text_inputs = ["Site", "https://site.com", "admin", "secret"]
    mocker.patch("akko.front.credentials_manage.st.text_input", side_effect=text_inputs)

    make_form = cast(
        Callable[[str], dict[str, Any]],
        _get_private("_make_credential_form"),
    )

    form_data = make_form("Website")

    assert form_data["name"] == "Site"
    assert form_data["url"] == "https://site.com"
    assert form_data["username"] == "admin"
    assert form_data["password"] == "secret"  # noqa: S105 # pragma: allowlist secret
    assert form_data["validation"] == (
        "Site" and "https://site.com" and "admin" and "secret"
    )


def test_make_credential_form_website_incomplete(mocker: MockerFixture) -> None:
    text_inputs = ["Site", "", "admin", "secret"]
    mocker.patch("akko.front.credentials_manage.st.text_input", side_effect=text_inputs)

    make_form = cast(
        Callable[[str], dict[str, Any]],
        _get_private("_make_credential_form"),
    )

    form_data = make_form("Website")

    assert form_data["validation"] == ""


def test_make_credential_form_linux_server(mocker: MockerFixture) -> None:
    text_inputs = ["Server", "192.168.1.1", "root", "password"]
    mocker.patch("akko.front.credentials_manage.st.text_input", side_effect=text_inputs)

    make_form = cast(
        Callable[[str], dict[str, Any]],
        _get_private("_make_credential_form"),
    )

    form_data = make_form("Linux Server")

    assert form_data["name"] == "Server"
    assert form_data["hostname"] == "192.168.1.1"
    assert form_data["username"] == "root"
    assert form_data["password"] == "password"  # noqa: S105 # pragma: allowlist secret
    assert form_data["validation"] == (
        "Server" and "192.168.1.1" and "root" and "password"
    )


def test_make_credential_form_gitlab_token(mocker: MockerFixture) -> None:
    mocker.patch(
        "akko.front.credentials_manage.st.text_input",
        side_effect=["API Token", "glpat-xyz"],  # pragma: allowlist secret
    )
    mocker.patch("akko.front.credentials_manage.st.checkbox", return_value=True)
    mocker.patch(
        "akko.front.credentials_manage.st.date_input", return_value=date(2026, 12, 31)
    )

    make_form = cast(
        Callable[[str], dict[str, Any]],
        _get_private("_make_credential_form"),
    )

    form_data = make_form("GitLab Token")

    assert form_data["name"] == "API Token"
    assert form_data["token"] == "glpat-xyz"  # noqa: S105
    assert form_data["expires"] is True
    assert form_data["expiration_date"] == date(2026, 12, 31)
    assert form_data["validation"] is True


def test_make_credential_form_gitlab_token_no_expiry(mocker: MockerFixture) -> None:
    mocker.patch(
        "akko.front.credentials_manage.st.text_input",
        side_effect=["CI Token", "glpat-abc"],  # pragma: allowlist secret
    )
    mocker.patch("akko.front.credentials_manage.st.checkbox", return_value=False)
    mocker.patch(
        "akko.front.credentials_manage.st.date_input", return_value=date(2026, 12, 31)
    )

    make_form = cast(
        Callable[[str], dict[str, Any]],
        _get_private("_make_credential_form"),
    )

    form_data = make_form("GitLab Token")

    assert form_data["expires"] is False
    assert form_data["validation"] is True


def test_make_credential_form_unsupported_type() -> None:
    make_form = cast(
        Callable[[str], dict[str, Any]],
        _get_private("_make_credential_form"),
    )

    with pytest.raises(NotImplementedError, match="not implemented"):
        make_form("Unsupported Type")
