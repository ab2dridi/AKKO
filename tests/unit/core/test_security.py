from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import orjson
import pytest
from cryptography.fernet import Fernet
from pydantic import AnyUrl
from pytest_mock import MockerFixture

import akko.core.security as security
from akko.typing.credentials import WebsiteCredential


def test_derive_key_is_reproducible() -> None:
    key = security.derive_key("super-secret")

    assert isinstance(key, bytes)
    assert base64.urlsafe_b64decode(key)
    assert security.derive_key("super-secret") == key


def test_load_data_returns_empty_when_file_missing(tmp_path: Path) -> None:
    key = security.derive_key("password")
    fernet = Fernet(key)

    assert security.load_data(fernet, file_path=tmp_path / "missing.enc") == []


def test_load_data_raises_for_invalid_password(tmp_path: Path) -> None:
    file_path = tmp_path / "credentials.enc"
    wrong_key = security.derive_key("wrong")
    wrong_fernet = Fernet(wrong_key)
    file_path.write_bytes(wrong_fernet.encrypt(orjson.dumps([])))

    fernet = Fernet(security.derive_key("right"))

    with pytest.raises(ValueError, match="Invalid master password"):
        security.load_data(fernet, file_path=file_path)


def test_load_data_validates_credentials(
    tmp_path: Path,
    isolated_credential_registry: dict[str, type[WebsiteCredential]],
) -> None:
    isolated_credential_registry["🌐 Website"] = WebsiteCredential
    payload: list[tuple[str, dict[str, object]]] = [
        (
            "🌐 Website",
            {
                "name": "Example",
                "url": "https://example.com",
                "username": "user",
                "password": "secret",  # pragma: allowlist secret
            },
        ),
        ("Unknown", {"ignored": True}),
    ]
    file_path = tmp_path / "credentials.enc"
    fernet = Fernet(security.derive_key("password"))
    file_path.write_bytes(fernet.encrypt(orjson.dumps(payload)))

    result = security.load_data(fernet, file_path=file_path)

    assert len(result) == 1
    cred_type, credential = result[0]
    assert cred_type == "🌐 Website"
    assert isinstance(credential, WebsiteCredential)
    assert credential.name == "Example"
    assert credential.password.get_secret_value() == "secret"


def test_load_data_raises_type_error_on_invalid_model(
    tmp_path: Path,
    isolated_credential_registry: dict[str, type[WebsiteCredential]],
) -> None:
    isolated_credential_registry["🌐 Website"] = WebsiteCredential
    payload: list[tuple[str, dict[str, object]]] = [
        (
            "🌐 Website",
            {
                "name": "Example",
                "url": "https://example.com",
                "username": "user",
                # missing password field
            },
        ),
    ]
    file_path = tmp_path / "credentials.enc"
    fernet = Fernet(security.derive_key("password"))
    file_path.write_bytes(fernet.encrypt(orjson.dumps(payload)))

    with pytest.raises(TypeError, match="Invalid credential data format"):
        security.load_data(fernet, file_path=file_path)


def test_save_data_encrypts_payload(tmp_path: Path) -> None:
    credential = WebsiteCredential.model_validate(
        {
            "name": "Example",
            "url": "https://example.com",
            "username": "user",
            "password": "secret",  # pragma: allowlist secret
        }
    )
    data: list[tuple[str, security.CredentialUnion]] = [
        ("🌐 Website", cast(security.CredentialUnion, credential))
    ]
    file_path = tmp_path / "credentials.enc"
    fernet = Fernet(security.derive_key("password"))

    security.save_data(data, fernet, file_path=file_path)

    decrypted = fernet.decrypt(file_path.read_bytes())
    decoded = orjson.loads(decrypted)
    assert decoded == [
        [
            "🌐 Website",
            {
                "name": "Example",
                "url": "https://example.com/",
                "username": "user",
                "password": "secret",  # pragma: allowlist secret
            },
        ]
    ]


def test_load_links_uses_settings_paths(tmp_path: Path, mocker: MockerFixture) -> None:
    private_file = tmp_path / "private.json"
    public_file = tmp_path / "public.json"
    settings_stub = SimpleNamespace(
        private_links_file=private_file,
        public_links_file=public_file,
    )
    mocker.patch.object(security, "SETTINGS", settings_stub)

    app_data = security.load_links()

    assert app_data.private.links == []
    assert app_data.public.links == []
    assert private_file.exists()
    assert public_file.exists()


def test_save_links_writes_both_collections(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    private_file = tmp_path / "private.json"
    public_file = tmp_path / "public.json"
    settings_stub = SimpleNamespace(
        private_links_file=private_file,
        public_links_file=public_file,
    )
    mocker.patch.object(security, "SETTINGS", settings_stub)
    links = security.ApplicationData(
        private=security.LinkCollection(
            links=[
                security.LinkEntry(
                    title="Private",
                    url=cast(AnyUrl, "https://private.example.com"),
                    category="infra",
                )
            ]
        ),
        public=security.LinkCollection(
            links=[
                security.LinkEntry(
                    title="Public",
                    url=cast(AnyUrl, "https://public.example.com"),
                    category="docs",
                )
            ]
        ),
    )

    security.save_links(links)

    private_payload = orjson.loads(private_file.read_text(encoding="utf-8"))
    public_payload = orjson.loads(public_file.read_text(encoding="utf-8"))

    assert private_payload["links"][0]["title"] == "Private"
    assert public_payload["links"][0]["title"] == "Public"
