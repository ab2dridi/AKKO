from collections.abc import Callable
from datetime import datetime
from typing import TypeAlias, cast

import streamlit as st
from cryptography.fernet import Fernet
from streamlit.delta_generator import DeltaGenerator

from akko.core.security import save_data
from akko.front.helpers import try_copy
from akko.settings import find_package_path
from akko.typing.credentials import (
    CredentialPayload,
    GitLabTokenCredential,
    LinuxServerCredential,
    NormalizedCredentialName,
    WebsiteCredential,
    clean_name_relation,
    credential_registry,
)

STYLE_PATH = find_package_path() / "resources" / "credentials.css"
TYPE_ORDER = [*credential_registry.keys(), "All"]
TYPE_FILTER_MAP: dict[str, str | None] = {**clean_name_relation(), "All": None}
ICON_MAP = {
    "Website": "🌐",
    "Linux Server": "🐧",
    "GitLab Token": "🔑",
}
DEFAULT_ICON = "🔐"
SEARCH_FIELDS = ("name", "url", "username", "hostname", "token")
TYPE_TO_CLEAN_NAME = clean_name_relation()

Renderer: TypeAlias = Callable[[list[DeltaGenerator], CredentialPayload, int], None]


def _render_search_box() -> str:
    """Render the quick search input and return the normalized query."""
    return (
        st.text_input("🔎 Quick search (name, URL, user, host...)", "").strip().lower()
        or ""
    )


def _render_type_filter() -> NormalizedCredentialName | None:
    """Render the type filter radio buttons and return the chosen type."""
    st.markdown("### 🔍 Filter by type")
    selection = st.radio("", TYPE_ORDER, horizontal=True, index=len(TYPE_ORDER) - 1)
    mapped = TYPE_FILTER_MAP.get(selection)
    if mapped is None:
        return None
    return cast(NormalizedCredentialName, mapped)


def _filter_credentials(
    data: list[CredentialPayload],
    query: str,
    selected_type: NormalizedCredentialName | None,
) -> list[CredentialPayload]:
    """Filter credentials using the provided query and type filter.

    Args:
        data (list[CredentialPayload]): Credential entries to filter.
        query (str): Normalized search query used for filtering.
        selected_type (NormalizedCredentialName | None): Credential type to keep,
            or ``None`` to keep every type.

    Returns:
        list[CredentialPayload]: Credentials matching the query and type.

    """
    filtered: list[CredentialPayload] = []
    for item in data:
        normalized_type = TYPE_TO_CLEAN_NAME.get(item[0], item[0].strip())
        if selected_type is not None and normalized_type != selected_type:
            continue
        filtered.append(item)

    if not query:
        return filtered

    return [item for item in filtered if _matches_query(item, query)]


def _matches_query(item: CredentialPayload, query: str) -> bool:
    """Return True when *item* matches the search query.

    Args:
        item (CredentialPayload): Credential entry being inspected.
        query (str): Normalized search query.

    Returns:
        bool: ``True`` when the credential matches the query.

    """
    item_dict = item[1].model_dump()
    for field in SEARCH_FIELDS:
        value = item_dict.get(field)
        if value and query in str(value).lower():
            return True
    return False


def _inject_styles() -> None:
    """Apply the shared card styles once before rendering cards."""
    st.markdown(
        f"\n<style>\n{STYLE_PATH.read_text()}\n</style>\n",
        unsafe_allow_html=True,
    )


def _render_copy_button(label: str, key: str, value: str, toast_label: str) -> None:
    """Render a copy button and trigger clipboard copy on click.

    Args:
        label (str): Text shown on the button.
        key (str): Streamlit widget key for the button.
        value (str): Raw value to copy to the clipboard.
        toast_label (str): Label used in the toast notification.

    """
    if st.button(label, key=key):
        try_copy(value, toast_label)


def _render_secret_field(
    field_label: str,
    value: str,
    key_prefix: str,
    idx: int,
    toast_label: str,
    mask_length: int = 8,
) -> None:
    """Render a masked text field with a show toggle and copy button.

    Args:
        field_label (str): Label displayed for the secret field.
        value (str): Secret value to display or copy.
        key_prefix (str): Prefix used to build unique Streamlit keys.
        idx (int): Index of the credential for widget key disambiguation.
        toast_label (str): Label used in copy confirmation toasts.
        mask_length (int): Number of characters shown when masking the value.

    """
    st.write(f"**{field_label}:**")
    show_value = st.checkbox("Show", key=f"{key_prefix}_show_{idx}")
    display_value = value if show_value else "•" * mask_length
    st.code(display_value, language="")
    button_label = f"📋 Copy {toast_label.lower()}"
    _render_copy_button(button_label, f"{key_prefix}_copy_{idx}", value, toast_label)


def _render_website_credentials(
    cols: list[DeltaGenerator], item: CredentialPayload, idx: int
) -> None:
    """Render the three-column layout for website credentials.

    Args:
        cols (list[DeltaGenerator]): Columns available for rendering fields.
        item (CredentialPayload): Pair of normalized type and credential data.
        idx (int): Index of the credential for widget key disambiguation.

    """
    typed_credential = cast(WebsiteCredential, item[1])
    url = str(typed_credential.url)
    username = typed_credential.username
    password = typed_credential.password.get_secret_value()

    with cols[0]:
        st.write("**URL:**")
        if url:
            st.markdown(f"[🌐 Open link]({url})", unsafe_allow_html=True)
        st.code(url, language="")
        _render_copy_button("📋 Copy URL", f"url_{idx}", url, "URL")

    with cols[1]:
        st.write("**Username:**")
        st.code(username, language="")
        _render_copy_button("📋 Copy username", f"user_{idx}", username, "Username")

    with cols[2]:
        _render_secret_field("Password", password, "pass", idx, "Password")


def _render_linux_server_credentials(
    cols: list[DeltaGenerator], item: CredentialPayload, idx: int
) -> None:
    """Render the three-column layout for Linux server credentials.

    Args:
        cols (list[DeltaGenerator]): Columns available for rendering fields.
        item (CredentialPayload): Pair of normalized type and credential data.
        idx (int): Index of the credential for widget key disambiguation.

    """
    typed_credential = cast(LinuxServerCredential, item[1])
    hostname = str(typed_credential.hostname)
    username = typed_credential.username
    password = typed_credential.password.get_secret_value()

    with cols[0]:
        st.write("**Hostname / IP:**")
        st.code(hostname, language="")
        _render_copy_button("📋 Copy host", f"host_{idx}", hostname, "Hostname")

    with cols[1]:
        st.write("**Username:**")
        st.code(username, language="")
        _render_copy_button("📋 Copy username", f"user_{idx}", username, "Username")

    with cols[2]:
        _render_secret_field("Password", password, "pass", idx, "Password")


def _render_gitlab_token_credentials(
    cols: list[DeltaGenerator], item: CredentialPayload, idx: int
) -> None:
    """Render the three-column layout for GitLab token credentials.

    Args:
        cols (list[DeltaGenerator]): Columns available for rendering fields.
        item (CredentialPayload): Pair of normalized type and credential data.
        idx (int): Index of the credential for widget key disambiguation.

    """
    typed_credential = cast(GitLabTokenCredential, item[1])
    token = typed_credential.token.get_secret_value()
    expires = typed_credential.expires
    expiration_date = typed_credential.expiration_date

    with cols[0]:
        _render_secret_field(
            "Token",
            token,
            "token",
            idx,
            "GitLab Token",
            mask_length=12,
        )

    with cols[1]:
        _render_token_status(expires=expires, expiration_date=expiration_date)

    with cols[2]:
        st.write("**Metadata:**")
        st.markdown(f"Expires: **{'Yes' if expires else 'No'}**")


def _render_token_status(*, expires: bool, expiration_date: str | None) -> None:
    """Display the token expiration status with contextual feedback.

    Args:
        expires (bool): Whether the token expires.
        expiration_date (str | None): ISO-formatted expiration date, when set.

    """
    if not expires or not expiration_date:
        st.info("🔒 Token without expiration.")
        return

    try:
        expiration = datetime.fromisoformat(expiration_date)
    except Exception:
        st.error("Error reading expiration date.")
        return

    remaining_days = (expiration - datetime.now()).days
    if remaining_days < 0:
        st.error(f"⛔ Expired {abs(remaining_days)} days ago.")
    elif remaining_days <= 7:
        st.warning(f"⚠️ Expires in {remaining_days} days.")
    else:
        st.success(f"✅ Valid ({remaining_days} days left).")


def _render_generic_details(
    cols: list[DeltaGenerator], item: CredentialPayload
) -> None:
    """Fallback renderer for credentials with an unknown type.

    Args:
        cols (list[DeltaGenerator]): Columns used for the fallback details.
        item (CredentialPayload): Credential entry to display.

    """
    with cols[0]:
        st.write("**Details:**")
        st.json({"credential type": item[0], "credential value": item[1].model_dump()})


CREDENTIAL_RENDERERS: dict[str, Renderer] = {
    "Website": _render_website_credentials,
    "Linux Server": _render_linux_server_credentials,
    "GitLab Token": _render_gitlab_token_credentials,
}


def _credential_icon(cred_type: str) -> str:
    """Return the emoji representing the credential type.

    Args:
        cred_type (str): Canonical credential type name.

    Returns:
        str: Emoji to display for the credential type.

    """
    return ICON_MAP.get(cred_type, DEFAULT_ICON)


def _render_delete_action(
    column: DeltaGenerator,
    idx: int,
    data: list[CredentialPayload],
    item: CredentialPayload,
    fernet: Fernet,
) -> None:
    """Render the delete button and handle the associated action.

    Args:
        column (DeltaGenerator): Column used to render the delete controls.
        idx (int): Index of the credential in the rendered list.
        data (list[CredentialPayload]): Mutable credential store to update.
        item (CredentialPayload): Credential entry targeted for deletion.
        fernet (Fernet): Encryption helper used when persisting data.

    """
    with column:
        if st.button("🗑️ Delete", key=f"del_{idx}"):
            data.remove(item)
            save_data(data, fernet)
            st.success("✅ Credential deleted.")
            st.rerun()


def _render_credential_card(
    idx: int,
    item: CredentialPayload,
    data: list[CredentialPayload],
    fernet: Fernet,
) -> None:
    """Render a credential card with type-specific details and controls.

    Args:
        idx (int): Index of the credential in the filtered list.
        item (CredentialPayload): Credential entry to render.
        data (list[CredentialPayload]): Credential store used for mutations.
        fernet (Fernet): Encryption helper used when persisting updates.

    """
    cred_type = TYPE_TO_CLEAN_NAME.get(item[0], item[0].strip())
    name = item[1].name or "(no name)"
    icon = _credential_icon(cred_type)
    type_display = cred_type or "Unknown"

    label = f"{icon} {name} ({type_display})"

    with st.expander(label, expanded=False):
        columns = st.columns([3, 3, 3, 2])
        renderer = CREDENTIAL_RENDERERS.get(cred_type)

        if renderer:
            renderer(columns[:3], item, idx)
        else:
            _render_generic_details(columns[:3], item)

        _render_delete_action(columns[3], idx, data, item, fernet)


def show_credentials(data: list[CredentialPayload], fernet: Fernet) -> None:
    """Display and manage stored credentials.

    Args:
        data (list[CredentialPayload]): Credential store to display.
        fernet (Fernet): Encryption helper passed to state-changing actions.

    """
    st.subheader("📂 Your credentials")

    if not data:
        st.info("No credentials stored yet.")
        return

    query = _render_search_box()
    selected_type = _render_type_filter()
    filtered = _filter_credentials(data, query, selected_type)

    if not filtered:
        st.warning("No credentials match your search.")
        return

    _inject_styles()

    for idx, item in enumerate(filtered):
        _render_credential_card(idx, item, data, fernet)
