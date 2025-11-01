"""Application settings management using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import orjson
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

import akko


def find_package_path() -> Path:
    """Find the path to the installed AKKO package.

    Returns:
        pathlib.Path: The path to the installed AKKO package directory.
    """
    init_path = Path(akko.__file__)

    return init_path.parent


CONFIG_FILENAME = "config.json"


def _resources_dir() -> Path:
    """Get the resources folder path.

    Returns:
        Path: the resources folder path
    """
    return find_package_path() / "resources"


def _default_config_template() -> Path:
    """Get the default config path.

    Raises:
        FileNotFoundError: default config file is missing

    Returns:
        Path: the path to the default config file
    """
    resources_dir = _resources_dir()
    for name in ("default-config.json", "default_config.json"):
        candidate = resources_dir / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Default configuration template not found.")


def _find_existing_config(start_dir: Path) -> Path | None:
    """Try and find the config file in the start_dir or its parents.

    Args:
        start_dir (Path): The directory to start the search from.

    Returns:
        Path | None: The path to the config file if found, otherwise None.
    """
    for directory in (start_dir, *start_dir.parents):
        candidate = directory / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def ensure_config_file(start_dir: Path | None = None) -> Path:
    """Ensure a configuration file exists starting from *start_dir*.

    If no ``config.json`` is found in *start_dir* or its parents, a copy of the
    default configuration file is placed in *start_dir*.

    Args:
        start_dir (Path | None): The directory to start the search from.
            Defaults to the current working directory.

    Returns:
        Path: The path to the configuration file.
    """
    base_dir = start_dir or Path.cwd()
    existing = _find_existing_config(base_dir)
    if existing is not None:
        return existing

    destination = base_dir / CONFIG_FILENAME
    template_path = _default_config_template()
    destination.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


class DataPaths(BaseModel):
    """Disk locations used by the application.

    credentials: Path to the credentials storage file.
    private_links: Path to the private links storage file.
    public_links: Path to the public links storage file.
    """

    model_config = ConfigDict(extra="forbid")

    credentials: Path = Field(description="Path to the credentials storage file.")
    private_links: Path = Field(description="Path to the private links storage file.")
    public_links: Path = Field(description="Path to the public links storage file.")


class FeatureFlags(BaseModel):
    """Configuration toggles for optional components.

    allow_public_links: Whether to enable public links feature.
    show_icons: Whether to display icons alongside links.
    """

    model_config = ConfigDict(extra="forbid")

    allow_public_links: bool = Field(
        description="Whether to enable public links feature."
    )
    show_icons: bool = Field(description="Whether to display icons alongside links.")


class SecurityConfig(BaseModel):
    """Security-related options.

    auto_lock_minutes: Minutes of inactivity before auto-locking the vault.
    hash_check: Whether to enable hash checking for credentials.
    """

    model_config = ConfigDict(extra="forbid")

    auto_lock_minutes: int = Field(
        ge=0, description="Minutes of inactivity before auto-locking the vault."
    )
    hash_check: bool = Field(
        description="Whether to enable hash checking for credentials."
    )


class ThemeConfig(BaseModel):
    """Streamlit theme customisation parameters.

    accent_color: Primary accent color.
    compact_view: Whether to use a compact layout.
    font: Font family to use.
    mode: Light or dark mode.
    secondary_color: Secondary color for accents.
    """

    model_config = ConfigDict(extra="forbid")

    accent_color: str
    compact_view: bool
    font: str
    mode: str
    secondary_color: str


class AkkoSettings(BaseSettings):
    """Validated AKKO configuration.

    data_paths: Paths to various data files used by the application.
    features: Feature flags to enable or disable optional components.
    security: Security-related configuration options.
    theme: Theme customization settings.
    """

    model_config = SettingsConfigDict(extra="forbid")

    app_name: str
    data_paths: DataPaths
    features: FeatureFlags
    security: SecurityConfig
    theme: ThemeConfig
    config_path: Path = Field(default_factory=Path.cwd, exclude=True)

    def resolve_path(self: AkkoSettings, path: Path | str) -> Path:
        """Resolve *path* relative to the configuration file location.

        Args:
            path (Path | str): The path to resolve.

        Returns:
            Path: The resolved absolute path.
        """
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return (self.config_path.parent / candidate).resolve()

    @property
    def credentials_file(self: AkkoSettings) -> Path:
        """Get the credential file path.

        Args:
            self (AkkoSettings): The settings instance.

        Returns:
            Path: The resolved credentials file path.
        """
        return self.resolve_path(self.data_paths.credentials)

    @property
    def private_links_file(self: AkkoSettings) -> Path:
        """Get the private links file path.

        Args:
            self (AkkoSettings): The settings instance.

        Returns:
            Path: The resolved private links file path.
        """
        return self.resolve_path(self.data_paths.private_links)

    @property
    def public_links_file(self: AkkoSettings) -> Path:
        """Get the public links file path.

        Args:
            self (AkkoSettings): The settings instance.

        Returns:
            Path: The resolved public links file path.
        """
        return self.resolve_path(self.data_paths.public_links)

    @property
    def icons_directory(self: AkkoSettings) -> Path:
        """Get the icons directory path.

        Args:
            self (AkkoSettings): The settings instance.

        Returns:
            Path: The resolved icons directory path.
        """
        return self.public_links_file.parent / "icons"


def _load_raw_config(config_path: Path) -> dict[str, Any]:
    """Load the json file into a python dictionary.

    Args:
        config_path (Path): The path to the configuration file.

    Raises:
        ValueError: If the configuration file is invalid.

    Returns:
        dict[str, Any]: The loaded configuration data.
    """
    try:
        raw_config: dict[str, Any] = orjson.loads(
            config_path.read_text(encoding="utf-8")
        )
    except orjson.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {config_path}: {exc}") from exc
    else:
        return raw_config


def _build_settings() -> AkkoSettings:
    """Build the settings from the config file.

    Raises:
        ValueError: if the configuration is invalid.

    Returns:
        AkkoSettings: The validated settings instance.
    """
    config_path = ensure_config_file()
    raw_config = _load_raw_config(config_path)
    try:
        settings = AkkoSettings.model_validate(raw_config)
    except ValidationError as exc:  # pragma: no cover - configuration errors
        message = "Configuration validation failed"
        raise ValueError(message) from exc
    else:
        return settings.model_copy(update={"config_path": config_path})


@lru_cache(maxsize=1)
def get_settings() -> AkkoSettings:
    """Return the cached settings instance.

    Returns:
        AkkoSettings: The validated settings instance.
    """
    return _build_settings()


def reload_settings() -> AkkoSettings:
    """Clear the settings cache and reload the configuration.

    Returns:
        AkkoSettings: The validated settings instance.
    """
    get_settings.cache_clear()
    return get_settings()


__all__ = [
    "AkkoSettings",
    "ensure_config_file",
    "get_settings",
    "reload_settings",
]
