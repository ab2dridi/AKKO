import base64
import hashlib
from pathlib import Path
from typing import Any

import orjson
from cryptography.fernet import Fernet, InvalidToken
from pydantic import ValidationError

from akko.settings import get_settings
from akko.typing.credentials import CredentialUnion, credential_registry
from akko.typing.security import ApplicationData, LinkCollection, LinkEntry

SETTINGS = get_settings()


# --- Encryption helpers ---
def derive_key(master_password: str) -> bytes:
    """Derive a Fernet-compatible key from the given master password."""
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


def save_data(
    data: list[tuple[str, CredentialUnion]],
    fernet: Fernet,
    file_path: Path = SETTINGS.credentials_file,
) -> None:
    """Encrypt and save credentials data to disk.

    Args:
        data (list[CredentialUnion]): List of credential entries.
        fernet (Fernet): Fernet instance initialized with the derived key.
        file_path (Path): Path to the data file.

    """
    payload = orjson.dumps(data, option=orjson.OPT_INDENT_2)
    encrypted = fernet.encrypt(payload)
    file_path.write_bytes(encrypted)


# --- Links management ---
def _empty_link_collection() -> LinkCollection:
    """Return an empty link collection."""
    category_list: list[str] = []
    link_list: list[LinkEntry] = []
    return LinkCollection(categories=category_list, links=link_list)


def _init_links_file(path: Path) -> LinkCollection:
    """Create an empty link file if it doesn't exist."""
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
    """Save public and private links into their respective JSON files."""
    links.private.model_dump_json(indent=2, ensure_ascii=False)
    SETTINGS.private_links_file.write_text(
        links.private.model_dump_json(indent=2, ensure_ascii=False)
    )
    SETTINGS.public_links_file.write_text(
        links.public.model_dump_json(indent=2, ensure_ascii=False)
    )
