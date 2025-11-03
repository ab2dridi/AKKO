import base64
import hashlib
from pathlib import Path
from typing import Any, TypeAlias, cast

import orjson
from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr, ValidationError

from akko.settings import get_settings
from akko.typing.credentials import CredentialUnion, credential_registry
from akko.typing.security import ApplicationData, LinkCollection, LinkEntry

SETTINGS = get_settings()


# --- Encryption helpers ---
def derive_key(master_password: str) -> bytes:
    """Derive a Fernet-compatible key from the given master password.

    Args:
        master_password (str): The master password provided by the user.

    Returns:
        bytes: A base64-encoded key suitable for Fernet.
    """
    key = hashlib.sha256(master_password.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key)


# --- Credentials management ---
def load_data(
    fernet: Fernet, file_path: Path = SETTINGS.credentials_file
) -> list[tuple[str, CredentialUnion]]:
    """Load and decrypt credentials data.

    - Returns [] if the file doesn't exist (new vault scenario).
    - Raises ValueError on invalid password.
    - Raises TypeError on invalid data format.

    Args:
        fernet (Fernet): Fernet instance initialized with the derived key.
        file_path (Path): Path to the data file.

    Returns:
        list[tuple[str, CredentialUnion]]: List of credential entries.
    """
    if not file_path.exists():
        return []
    encrypted: bytes = file_path.read_bytes()
    try:
        decrypted = fernet.decrypt(encrypted)
    except InvalidToken as e:
        # report invalid password
        raise ValueError("Invalid master password") from e
    data: list[tuple[str, dict[str, Any]]] = orjson.loads(decrypted.decode("utf-8"))
    if not isinstance(data, list):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError("Invalid credential data format")

    try:
        result: list[tuple[str, CredentialUnion]] = [
            (_type, credential_registry.get(_type).model_validate(credential))  # type: ignore[union-attr]
            for _type, credential in data
            if _type in credential_registry
        ]
    except ValidationError as e:
        raise TypeError("Invalid credential data format") from e
    else:
        return result


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


def _to_serializable(value: object) -> JSONValue:
    """Convert nested Pydantic objects to JSON-serializable payloads.

    Args:
        value (object): The value to convert.

    Returns:
        JSONValue: The JSON-serializable representation of the input value.
    """
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, dict):
        dict_value = cast(dict[object, object], value)
        result: dict[str, JSONValue] = {}
        for key, val in dict_value.items():
            result[str(key)] = _to_serializable(val)
        return result
    if isinstance(value, list):
        list_value = cast(list[object], value)
        return [_to_serializable(item) for item in list_value]
    if isinstance(value, tuple):
        tuple_value = cast(tuple[object, ...], value)
        return [_to_serializable(item) for item in tuple_value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def save_data(
    data: list[tuple[str, CredentialUnion]],
    fernet: Fernet,
    file_path: Path = SETTINGS.credentials_file,
) -> None:
    """Encrypt and persist credential entries to disk.

    Args:
        data: Sequence of credential type names and their validated models.
        fernet: Active Fernet instance used for symmetric encryption.
        file_path: Destination JSON file path for the encrypted payload.
    """
    serializable: list[tuple[str, dict[str, JSONValue]]] = []
    for credential_type, credential in data:
        serialized = cast(
            dict[str, JSONValue], _to_serializable(credential.model_dump())
        )
        serializable.append((credential_type, serialized))
    payload = orjson.dumps(serializable, option=orjson.OPT_INDENT_2)
    encrypted = fernet.encrypt(payload)
    file_path.write_bytes(encrypted)


# --- Links management ---
def _empty_link_collection() -> LinkCollection:
    """Return an empty link collection.

    Returns:
        LinkCollection: An empty LinkCollection instance.
    """
    category_list: list[str] = []
    link_list: list[LinkEntry] = []
    return LinkCollection(categories=category_list, links=link_list)


def _init_links_file(path: Path) -> LinkCollection:
    """Create an empty link file if it doesn't exist.

    Args:
        path (Path): Path to the link collection JSON file.
    """
    if not path.exists():
        data = _empty_link_collection()
        path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
        return data

    try:
        result = LinkCollection.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError:
        return _empty_link_collection()

    return result


def load_links() -> ApplicationData:
    """Load public and private links from separate JSON files."""
    private_links = _init_links_file(SETTINGS.private_links_file)
    pro_links = _init_links_file(SETTINGS.public_links_file)
    return ApplicationData(private=private_links, public=pro_links)


def save_links(links: ApplicationData) -> None:
    """Save public and private links into their respective JSON files.

    Args:
        links (ApplicationData): Application data containing link collections.
    """
    links.private.model_dump_json(indent=2, ensure_ascii=False)
    SETTINGS.private_links_file.write_text(
        links.private.model_dump_json(indent=2, ensure_ascii=False)
    )
    SETTINGS.public_links_file.write_text(
        links.public.model_dump_json(indent=2, ensure_ascii=False)
    )
