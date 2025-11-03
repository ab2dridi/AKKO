from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from pytest_mock import MockerFixture

import akko
import akko.settings as settings_module


def _read_default_config_template() -> str:
    resources_dir = settings_module.find_package_path() / "resources"
    for name in ("default-config.json", "default_config.json"):
        candidate = resources_dir / name
        if candidate.exists():
            return cast(str, candidate.read_text(encoding="utf-8"))  # type: ignore[redundant-cast, unused-ignore]
    raise AssertionError("Default configuration template not found for tests.")  # type: ignore[redundant-cast, unused-ignore]


def test_find_package_path_matches_akko_init() -> None:
    expected = Path(akko.__file__).parent.resolve()

    assert settings_module.find_package_path() == expected


def test_ensure_config_file_creates_copy_when_missing(tmp_path: Path) -> None:
    template_text = _read_default_config_template()

    config_path = settings_module.ensure_config_file(tmp_path)

    assert config_path.exists()
    assert config_path.read_text(encoding="utf-8") == template_text


def test_ensure_config_file_reuses_existing(tmp_path: Path) -> None:
    parent_config = tmp_path / settings_module.CONFIG_FILENAME
    parent_config.write_text("{}", encoding="utf-8")
    child_dir = tmp_path / "project"
    child_dir.mkdir()

    config_path = settings_module.ensure_config_file(child_dir)

    assert config_path == parent_config


def test_reload_settings_raises_on_invalid_json(
    tmp_path: Path,
    mocker: MockerFixture,
    reset_settings_cache: None,
) -> None:
    assert reset_settings_cache is None
    bad_config = tmp_path / "config.json"
    bad_config.write_text("not json", encoding="utf-8")

    mocker.patch("akko.settings.ensure_config_file", return_value=bad_config)

    with pytest.raises(ValueError, match="Invalid JSON"):
        settings_module.reload_settings()


def test_reload_settings_validates_payload(
    tmp_path: Path,
    mocker: MockerFixture,
    reset_settings_cache: None,
) -> None:
    assert reset_settings_cache is None
    template = _read_default_config_template()
    config_path = tmp_path / "config.json"
    config_path.write_text(template, encoding="utf-8")

    mocker.patch("akko.settings.ensure_config_file", return_value=config_path)

    result = settings_module.reload_settings()

    assert result.config_path == config_path
    assert result.credentials_file.parent.exists()
    assert result.private_links_file.parent.exists()
    assert result.public_links_file.parent.exists()


def test_get_settings_uses_cache(
    reset_settings_cache: None, mocker: MockerFixture
) -> None:
    assert reset_settings_cache is None
    first = object()
    mocker.patch("akko.settings._build_settings", return_value=first)

    assert settings_module.get_settings() is first
    assert settings_module.get_settings() is first


def test_reload_settings_rebuilds_instance(
    reset_settings_cache: None, mocker: MockerFixture
) -> None:
    assert reset_settings_cache is None
    first = object()
    second = object()
    mocker.patch(
        "akko.settings._build_settings",
        side_effect=[first, second],
    )

    assert settings_module.get_settings() is first
    assert settings_module.reload_settings() is second


def test_akko_settings_resolve_path_and_create_dirs(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    payload: dict[str, object] = {
        "app_name": "Test",
        "data_paths": {
            "credentials": "vault/credentials.enc",
            "private_links": "links/private.json",
            "public_links": "links/public.json",
        },
        "features": {"allow_public_links": True, "show_icons": False},
        "security": {"auto_lock_minutes": 5, "hash_check": True},
        "theme": {
            "accent_color": "#fff",
            "compact_view": True,
            "font": "Inter",
            "mode": "dark",
            "secondary_color": "#000",
        },
        "config_path": config_path,
    }

    settings = settings_module.AkkoSettings.model_validate(payload)

    resolved = settings.resolve_path("relative/file.txt")
    assert resolved == (config_dir / "relative/file.txt").resolve()
    assert settings.credentials_file.parent.exists()
    assert settings.private_links_file.parent.exists()
    assert settings.public_links_file.parent.exists()
    assert settings.icons_directory.exists()
