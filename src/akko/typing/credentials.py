from collections.abc import Callable
from re import compile
from typing import Literal, TypeAlias, TypeVar, cast, overload

from pydantic import AnyUrl, BaseModel, Field, IPvAnyAddress, SecretStr

BaseModelT = TypeVar("BaseModelT", bound=BaseModel)
credential_registry: dict[str, "BaseCredentialType"] = {}

NAME_CLEANER = compile(r"[^a-zA-Z0-9_\- ]+")


def clean_name_relation(
    registry: dict[str, "BaseCredentialType"] = credential_registry,
) -> dict[str, str]:
    """Create a mapping of normalized names to registry names."""
    return {name: NAME_CLEANER.sub("", name).strip() for name in registry}


def invert_clean_name_relation(
    registry: dict[str, "BaseCredentialType"] = credential_registry,
) -> dict[str, str]:
    """Invert a name relation mapping."""
    return {NAME_CLEANER.sub("", name).strip(): name for name in registry}


def register_credential(name: str) -> Callable[[type[BaseModelT]], type[BaseModelT]]:
    """Register a credential schema under ``name``."""

    def decorator(cls: type[BaseModelT]) -> type[BaseModelT]:
        if name in credential_registry:
            raise ValueError(f"Credential '{name}' already registered")
        credential_registry[name] = cls  # type: ignore[assignment]
        return cls

    return decorator


@register_credential("🌐 Website")
class WebsiteCredential(BaseModel):
    """Website credential object.

    Attributes:
        credential_type (Literal["website"]): The type of credential
        name (str): Name or description of the website
        url (AnyUrl): URL of the website
        username (str): Username for the website
        password (SecretStr): Password for the website
    """

    name: str = Field(..., description="Name or description of the website")
    url: AnyUrl = Field(..., description="URL of the website")
    username: str = Field(..., description="Username for the website")
    password: SecretStr = Field(..., description="Password for the website")

    @property
    def credential_type(self) -> str:
        """Get the credential type."""
        return "🌐 Website"


@register_credential("🐧 Linux Server")
class LinuxServerCredential(BaseModel):
    """Linux server credential object.

    Attributes:
        credential_type (Literal["linux server"]): The type of credential
        name (str): Name or description of the server
        hostname (AnyUrl|IPvAnyAddress|str): Hostname or IP address of the server
        username (str): Username for the server
        password (SecretStr): Password for the server
    """

    name: str = Field(..., description="Name or description of the server")
    hostname: AnyUrl | IPvAnyAddress | str = Field(
        ..., description="Hostname or IP address of the server"
    )
    username: str = Field(..., description="Username for the server")
    password: SecretStr = Field(..., description="Password for the server")

    @property
    def credential_type(self) -> str:
        """Get the credential type."""
        return "🐧 Linux Server"


@register_credential("🔑 GitLab Token")
class GitLabTokenCredential(BaseModel):
    """Bearer token credential object.

    Attributes:
        credential_type (Literal["gitlab token"]): The type of credential
        name (str): Name of the GitLab token
        token (SecretStr): Personal access token for GitLab
        expires (bool): Whether the token expires
        expiration_date (str | None): Expiration date of the token in ISO format
    """

    name: str = Field(..., description="Name of the GitLab token")
    token: SecretStr = Field(..., description="Personal access token for GitLab")
    expires: bool = Field(default=False, description="Whether the token expires")
    expiration_date: str | None = Field(
        None, description="Expiration date of the token in ISO format"
    )

    @property
    def credential_type(self) -> str:
        """Get the credential type."""
        return "🔑 GitLab Token"


# -------- registry manual interventions for pylance --------

CredentialUnion: TypeAlias = (
    WebsiteCredential | LinuxServerCredential | GitLabTokenCredential
)
CredentialPayload: TypeAlias = tuple[str, CredentialUnion]
BaseCredentialType = type[CredentialUnion]

NormalizedCredentialName = Literal["Website", "Linux Server", "GitLab Token"]


@overload
def get_credential_factory(name: Literal["Website"]) -> type[WebsiteCredential]: ...


@overload
def get_credential_factory(
    name: Literal["Linux Server"],
) -> type[LinuxServerCredential]: ...


@overload
def get_credential_factory(
    name: Literal["GitLab Token"],
) -> type[GitLabTokenCredential]: ...


def get_credential_factory(name: NormalizedCredentialName) -> type[CredentialUnion]:
    """Retrieve the concrete credential factory by its normalized name."""
    registry_name = invert_clean_name_relation().get(name)
    if registry_name is None:
        raise KeyError(f"Credential factory '{name}' is not registered.")

    factory = credential_registry[registry_name]
    if name == "Website":
        return cast(type[WebsiteCredential], factory)
    if name == "Linux Server":
        return cast(type[LinuxServerCredential], factory)
    if name == "GitLab Token":
        return cast(type[GitLabTokenCredential], factory)

    raise NotImplementedError(f"Credential factory '{name}' is not implemented.")
