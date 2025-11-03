from datetime import date
from typing import Any, cast

import streamlit as st
from cryptography.fernet import Fernet
from pydantic import ValidationError

from akko.core.security import save_data
from akko.typing.credentials import (
    CredentialUnion,
    NormalizedCredentialName,
    clean_name_relation,
    credential_registry,
    get_credential_factory,
)


def _persist_credential(
    data: list[tuple[str, CredentialUnion]],
    fernet: Fernet,
    credential: CredentialUnion,
) -> None:
    """Append credential to the in-memory store and persist the encrypted payload.

    Args:
        data (list[tuple[str, CredentialUnion]]): Mutable credential store.
        fernet (Fernet): Encryption helper used to serialize data to disk.
        credential (CredentialUnion): Credential instance to append.

    """
    data.append((credential.credential_type, credential))
    save_data(data, fernet)


def _make_credential_form(name: NormalizedCredentialName) -> dict[str, Any]:
    """Generate a form dictionary for the given credential type.

    Args:
        name (NormalizedCredentialName): Normalized credential type to render.

    Returns:
        dict[str, Any]: Raw form data gathered from Streamlit widgets.

    """
    form_data: dict[str, Any] = {}
    if name == "Website":
        form_data["name"] = st.text_input("Name / Description")
        form_data["url"] = st.text_input("URL")
        form_data["username"] = st.text_input("Username")
        form_data["password"] = st.text_input("Password", type="password")
        form_data["validation"] = (
            form_data["name"]
            and form_data["url"]
            and form_data["username"]
            and form_data["password"]
        )
    elif name == "Linux Server":
        form_data["name"] = st.text_input("Name / Description")
        form_data["hostname"] = st.text_input("Hostname / IP")
        form_data["username"] = st.text_input("Username")
        form_data["password"] = st.text_input("Password", type="password")
        form_data["validation"] = (
            form_data["name"]
            and form_data["hostname"]
            and form_data["username"]
            and form_data["password"]
        )
    elif name == "GitLab Token":
        form_data["name"] = st.text_input("Token name (e.g. API, CI/CD)")
        form_data["token"] = st.text_input("Personal access token", type="password")
        today = date.today()
        default_date = date(today.year, 12, 31)
        form_data["expires"] = st.checkbox("Token expires?", value=False)
        form_data["expiration_date"] = st.date_input(
            "Expiration date (ignored if unchecked)", value=default_date
        )
        form_data["validation"] = bool(form_data["name"] and form_data["token"])
    else:
        raise NotImplementedError(f"Credential type '{name}' is not implemented.")
    return form_data


def add_credential(data: list[tuple[str, CredentialUnion]], fernet: Fernet) -> None:
    """Add a new credential to the data list.

    Args:
        data (list[tuple[str, CredentialUnion]]): Credential store to update.
        fernet (Fernet): Encryption helper passed to persistence operations.

    """
    st.subheader("📝 New credential")

    selected_cred_type = st.radio(
        "Credential type",
        credential_registry.keys(),
        horizontal=True,
    )

    cred_type = cast(
        NormalizedCredentialName,
        clean_name_relation(credential_registry)[selected_cred_type],
    )

    with st.form("add_credential", clear_on_submit=True):
        form_data = _make_credential_form(cred_type)
        submitted = st.form_submit_button("Add")

    if not submitted:
        return

    is_valid = bool(form_data.pop("validation", False))
    if not is_valid:
        st.error("Please fill in all required fields before submitting.")
        return

    if cred_type == "GitLab Token":
        expiration_date = form_data.get("expiration_date")
        if not form_data.get("expires"):
            form_data["expiration_date"] = None
        elif isinstance(expiration_date, date):
            form_data["expiration_date"] = expiration_date.isoformat()

    factory = get_credential_factory(cred_type)

    try:
        credential = factory(**form_data)
    except ValidationError as exc:
        messages = "; ".join(err.get("msg", "Invalid value") for err in exc.errors())
        st.error(f"Invalid credential data: {messages}")
        return

    _persist_credential(data, fernet, credential)
    st.success("✅ Credential added.")
