from __future__ import annotations

import pytest
from pydantic import BaseModel, Field
from pytest_mock import MockerFixture

from akko.typing.credentials import (
    GitLabTokenCredential,
    LinuxServerCredential,
    NormalizedCredentialName,
    WebsiteCredential,
    clean_name_relation,
    credential_registry,
    get_credential_factory,
    invert_clean_name_relation,
    register_credential,
)


class DummyCredential(BaseModel):
    """Minimal credential model used in tests."""

    field: str = Field(...)


def test_clean_name_relation_strips_noise(
    isolated_credential_registry: dict[str, type[BaseModel]],
) -> None:
    registry = isolated_credential_registry
    registry["  Demo Credential!* "] = DummyCredential

    mapping = clean_name_relation()

    assert mapping == {"  Demo Credential!* ": "Demo Credential"}


def test_invert_clean_name_relation_restores_original_names(
    isolated_credential_registry: dict[str, type[BaseModel]],
) -> None:
    registry = isolated_credential_registry
    registry["My*Credential"] = DummyCredential

    mapping = invert_clean_name_relation()

    assert mapping == {"MyCredential": "My*Credential"}


def test_register_credential_adds_model_to_registry(
    isolated_credential_registry: dict[str, type[BaseModel]],
) -> None:
    registry = isolated_credential_registry

    @register_credential("Example Credential")
    class ExampleCredential(BaseModel):
        value: str = Field(...)

    assert registry["Example Credential"] is ExampleCredential


def test_register_credential_raises_when_name_already_registered(
    isolated_credential_registry: dict[str, type[BaseModel]],
) -> None:
    registry = isolated_credential_registry
    registry["Duplicate"] = DummyCredential

    with pytest.raises(ValueError, match=r"Credential 'Duplicate' already registered"):
        register_credential("Duplicate")(DummyCredential)


@pytest.mark.parametrize(
    ("normalized_name", "expected"),
    [
        ("Website", WebsiteCredential),
        ("Linux Server", LinuxServerCredential),  # type: ignore[list-item, unused-ignore]
        ("GitLab Token", GitLabTokenCredential),  # type: ignore[list-item, unused-ignore]
    ],
)
def test_get_credential_factory_returns_expected_class(
    normalized_name: NormalizedCredentialName,
    expected: type[BaseModel],
) -> None:
    factory = get_credential_factory(normalized_name)

    assert factory is expected


def test_get_credential_factory_raises_when_missing(
    mocker: MockerFixture,
) -> None:
    mocker.patch.dict(credential_registry, {}, clear=True)

    with pytest.raises(KeyError):
        get_credential_factory("Website")
