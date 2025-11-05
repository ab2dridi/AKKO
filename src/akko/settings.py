"""Application settings management using pydantic-settings."""

from __future__ import annotations

import atexit
import os
from contextlib import ExitStack
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Literal

import orjson
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

import akko
from akko.logging import configure_logger, get_logger


def find_package_path() -> Path:
    """Find the path to the installed AKKO package.

    Returns:
        pathlib.Path: The path to the installed AKKO package directory.
    """
    init_path = Path(akko.__file__)

    return init_path.parent.resolve()


CONFIG_FILENAME = "akko-config.json"


_RESOURCE_STACK = ExitStack()
atexit.register(_RESOURCE_STACK.close)


@lru_cache(maxsize=1)
def _resources_dir() -> Path:
    """Return the on-disk path to the bundled resources directory."""
    resource = resources.files("akko") / "resources"
    return _RESOURCE_STACK.enter_context(resources.as_file(resource))


def _launch_root() -> Path:
    """Return the directory where the launcher was invoked."""
    override = os.environ.get("AKKO_WORKDIR")
    if override:
        candidate = Path(override).expanduser()
        if candidate.exists() and not candidate.is_dir():
            return candidate.parent
        return candidate
    return Path.cwd()


def _default_config_template() -> str:
    """Load the default configuration template text.

    Raises:
        FileNotFoundError: default config file is missing

    Returns:
        str: The contents of the default configuration template.
    """
    resource_root = _resources_dir()
    for name in ("default-config.json", "default_config.json"):
        candidate = resource_root.joinpath(name)
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
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
    base_dir = start_dir or _launch_root()
    existing = _find_existing_config(base_dir)
    if existing is not None:
        return existing

    destination = base_dir / CONFIG_FILENAME
    destination.parent.mkdir(parents=True, exist_ok=True)
    template_content = _default_config_template()
    destination.write_text(template_content, encoding="utf-8")
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

    accent_color: str = Field(description="Primary accent color.")
    compact_view: bool = Field(description="Whether to use a compact layout.")
    font: str = Field(description="Font family to use.")
    mode: str = Field(description="Light or dark mode.")
    secondary_color: str = Field(description="Secondary color for accents.")


class DevConfig(BaseModel):
    """Development-related options.

    enable_debug: Whether to enable debug mode.
    log_level: Logging level for the application.
    """

    model_config = ConfigDict(extra="forbid")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        description="Logging level for the application."
    )

    @field_validator("log_level", mode="before")
    def validate_log_level(cls, value: str) -> str:
        """Validate the log level value.

        Args:
            value (str): The log level value to validate.

        Raises:
            ValueError: If the log level is not valid.

        Returns:
            str: The validated log level.
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
        upper_value = value.upper()
        if upper_value not in valid_levels:
            raise ValueError(
                f"Invalid log level: {value}. Must be one of {valid_levels}."
            )
        return upper_value


class AkkoSettings(BaseSettings):
    """Validated AKKO configuration.

    data_paths: Paths to various data files used by the application.
    features: Feature flags to enable or disable optional components.
    security: Security-related configuration options.
    theme: Theme customization settings.
    """

    model_config = SettingsConfigDict(extra="forbid")

    app_name: str = Field(default="AKKO", description="Name of the application")
    data_paths: DataPaths = Field(
        description="Paths to various data files used by the application."
    )
    features: FeatureFlags = Field(
        description="Feature flags to enable or disable optional components."
    )
    security: SecurityConfig = Field(
        description="Security-related configuration options."
    )
    theme: ThemeConfig = Field(description="Theme customization settings.")
    dev_mode: DevConfig = Field(
        description="Development-related configuration options."
    )
    config_path: Path = Field(
        default_factory=lambda: Path.cwd() / CONFIG_FILENAME, exclude=True
    )
    package_path: Path = Field(
        default_factory=find_package_path, exclude=True
    )

    @model_validator(mode="after")
    def _ensure_data_directories(self) -> AkkoSettings:
        """Create directories required by file-backed settings."""
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        self.private_links_file.parent.mkdir(parents=True, exist_ok=True)
        self.public_links_file.parent.mkdir(parents=True, exist_ok=True)
        return self

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
    def resources_path(self: AkkoSettings) -> Path:
        """Get the resources directory path."""
        return self.package_path / "resources"

    @property
    def credentials_file(self: AkkoSettings) -> Path:
        """Get the credential file path and ensure its directory exists.

        Args:
            self (AkkoSettings): The settings instance.

        Returns:
            Path: The resolved credentials file path.
        """
        file_path = self.resolve_path(self.data_paths.credentials)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

    @property
    def private_links_file(self: AkkoSettings) -> Path:
        """Get the private links file path and ensure its directory exists.

        Args:
            self (AkkoSettings): The settings instance.

        Returns:
            Path: The resolved private links file path.
        """
        file_path = self.resolve_path(self.data_paths.private_links)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

    @property
    def public_links_file(self: AkkoSettings) -> Path:
        """Get the public links file path and ensure its directory exists.

        Args:
            self (AkkoSettings): The settings instance.

        Returns:
            Path: The resolved public links file path.
        """
        file_path = self.resolve_path(self.data_paths.public_links)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

    @property
    def icons_directory(self: AkkoSettings) -> Path:
        """Get the icons directory path .

        Args:
            self (AkkoSettings): The settings instance.

        Returns:
            Path: The resolved icons directory path.
        """
        return self.package_path / "icons"


def _load_raw_config(config_path: Path) -> dict[str, Any]:
    """Load the json file into a python dictionary.

    Args:
        config_path (Path): The path to the configuration file.

    Raises:
        ValueError: If the configuration file is invalid.

    Returns:
        dict[str, Any]: The loaded configuration data.
    """
    if not config_path.is_file():
        raise ValueError(f"Configuration file not found: {config_path}")
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
    payload: dict[str, Any] = dict(raw_config)
    payload["config_path"] = config_path
    try:
        settings = AkkoSettings.model_validate(payload)
    except ValidationError as exc:  # pragma: no cover - configuration errors
        message = "Configuration validation failed"
        raise ValueError(message) from exc
    else:
        return settings


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


configure_logger(log_level=get_settings().dev_mode.log_level)
logger = get_logger("akko")

__all__ = [
    "AkkoSettings",
    "ensure_config_file",
    "get_settings",
    "reload_settings",
]
