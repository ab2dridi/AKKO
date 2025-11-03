from datetime import datetime, timedelta

import streamlit as st
from cryptography.fernet import Fernet

from akko.core.security import derive_key, load_data, load_links
from akko.front.credentials_list import show_credentials
from akko.front.credentials_manage import add_credential
from akko.front.links_page import show_links
from akko.settings import find_package_path, get_settings
from akko.typing.credentials import CredentialUnion

CSS_PATH = find_package_path() / "resources" / "app.css"

# --- Load configuration ---
settings = get_settings()
AUTO_LOCK_MINUTES = settings.security.auto_lock_minutes

# --- Page setup ---
st.set_page_config(page_title=settings.app_name, layout="wide", page_icon="🛡️")

# --- Custom CSS ---
st.markdown(
    f"""<style>\n{CSS_PATH.read_text()}\n</style>\n""",
    unsafe_allow_html=True,
)

# --- Sidebar Header ---
st.sidebar.markdown(
    f"""
    <div class='sidebar-title'>🛡️ {settings.app_name}</div>
    <div class='sidebar-sub'>Access Key • Keep Ownership</div>
    <div class='sidebar-quote'>"Your keys. Your control. Always offline."</div>
    <div class='sidebar-divider'></div>
    """,
    unsafe_allow_html=True,
)

# --- Sidebar Navigation ---
st.sidebar.header("Navigation")
page: str = st.sidebar.radio("Navigate to:", ["🔐 Credentials", "🔗 Links"], index=0)

# --- Session setup ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "last_activity" not in st.session_state:
    st.session_state["last_activity"] = datetime.now()


def check_auto_lock() -> None:
    """Check if the session should be auto-locked due to inactivity."""
    if st.session_state["authenticated"]:
        elapsed = datetime.now() - st.session_state["last_activity"]
        if elapsed > timedelta(minutes=AUTO_LOCK_MINUTES):
            st.session_state["authenticated"] = False
            st.session_state.pop("fernet", None)
            st.warning("🔒 Vault locked due to inactivity.")
            st.rerun()


def update_activity() -> None:
    """Update the last activity timestamp."""
    st.session_state["last_activity"] = datetime.now()


check_auto_lock()

fernet: Fernet | None = None
data: list[tuple[str, CredentialUnion]] = []
links = load_links()

# --- Credentials page ---
if page == "🔐 Credentials":
    if not st.session_state["authenticated"]:
        st.markdown(
            f"<h2 style='text-align:center;'>🛡️ {settings.app_name}</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            (
                "<p style='text-align:center; font-size:1.1rem;'>"
                "Access Key • Keep Ownership</p>"
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            (
                "<p style='text-align:center; font-size:1.1rem;'>"
                '"Your keys. Your control. Always offline."</p>'
            ),
            unsafe_allow_html=True,
        )
        st.markdown("---")

        master_password = st.text_input("Master password", type="password")
        if st.button("🔓 Unlock vault"):
            if not master_password.strip():
                st.warning("Please enter your master password.")
                st.stop()
            try:
                key = derive_key(master_password)
                fernet = Fernet(key)
                data_probe = load_data(fernet)
                st.session_state["fernet"] = fernet
                st.session_state["authenticated"] = True
                update_activity()
                if data_probe:
                    st.success("✅ Vault unlocked successfully.")
                else:
                    st.warning("🆕 New vault created (no existing credentials).")
                st.rerun()
            except ValueError:
                st.error("❌ Incorrect master password.")
            except Exception as e:
                st.error(f"Error while opening vault: {e}")
        st.stop()

    update_activity()
    fernet = st.session_state["fernet"]
    data = [] if fernet is None else load_data(fernet)

    if "show_form_creds" not in st.session_state:
        st.session_state["show_form_creds"] = False
    if st.button("➕ Toggle add credential form", type="primary"):  # noqa: RUF001
        st.session_state["show_form_creds"] = not st.session_state["show_form_creds"]
        update_activity()
    if st.session_state["show_form_creds"] and fernet is not None:
        add_credential(data, fernet)
        update_activity()
    if fernet is not None:
        show_credentials(data, fernet)
    update_activity()

# --- Links page ---
elif page == "🔗 Links":
    show_links()

# --- Footer ---
st.markdown("---")
st.caption(
    f"🛡️ {settings.app_name} — Auto-lock after {AUTO_LOCK_MINUTES} min inactivity"
)
st.caption(
    "💾 credentials.enc → private/ | private_links.json "
    "/ pro_links.json → separate files"
)
