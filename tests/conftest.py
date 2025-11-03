from __future__ import annotations

from collections.abc import Iterator
from typing import cast

import pytest
from pytest_mock import MockerFixture

from akko.typing.credentials import BaseCredentialType


@pytest.fixture
def reset_logger_state() -> Iterator[None]:
    """Reset akko logging configuration around a test."""
    from logging import getLogger

    from akko.logging import configure_logger

    configure_logger.cache_clear()
    root_logger = getLogger()
    root_logger.handlers.clear()

    yield

    root_logger.handlers.clear()
    configure_logger.cache_clear()
    configure_logger()


@pytest.fixture
def reset_settings_cache() -> Iterator[None]:
    """Reset cached settings around a test."""
    from akko.settings import get_settings

    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.fixture
def isolated_credential_registry(
    mocker: MockerFixture,
) -> dict[str, BaseCredentialType]:
    """Provide a clean credential registry for each test."""
    from akko.typing import credentials

    mocker.patch.dict(credentials.credential_registry, {}, clear=True)  # type: ignore[redundant-cast, unused-ignore]
    return cast(dict[str, BaseCredentialType], credentials.credential_registry)  # type: ignore[redundant-cast, unused-ignore]
