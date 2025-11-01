import streamlit as st
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from utils.security import derive_key, load_data, load_links
from utils.config_loader import load_config
from modules.credentials_list import show_credentials
from modules.credentials_manage import add_credential
from modules.links_page import show_links

# --- Load configuration ---
config = load_config()
AUTO_LOCK_MINUTES = config.get("security", {}).get("auto_lock_minutes", 5)

# --- Page setup ---
st.set_page_config(page_title=config["app_name"], layout="wide", page_icon="🛡️")

# --- Custom CSS ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        div.stButton > button {
            border-radius: 10px;
            font-weight: 600;
            background: linear-gradient(90deg, #00C9A7, #4F46E5);
            color: white;
            border: none;
            transition: 0.3s ease-in-out;
        }
        div.stButton > button:hover {
            transform: scale(1.03);
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        section[data-testid="stSidebar"] {
            background: rgba(255,255,255,0.65);
            backdrop-filter: blur(10px);
            border-right: 1px solid rgba(0,0,0,0.05);
        }
        /* Centrer le header dans la sidebar */
        .sidebar-title {
            text-align: center;
            font-weight: 700;
            font-size: 1.2rem;
            margin-top: 0.5rem;
            margin-bottom: 0.2rem;
        }
        .sidebar-sub {
            text-align: center;
            font-size: 0.9rem;
            color: #555;
            margin-bottom: 0.2rem;
        }
        .sidebar-quote {
            text-align: center;
            font-size: 0.85rem;
            color: #666;
            margin-bottom: 0.6rem;
        }
        .sidebar-divider {
            border-top: 1px solid rgba(0,0,0,0.1);
            margin: 0.5rem 0 1rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar Header ---
st.sidebar.markdown(
    f"""
    <div class='sidebar-title'>🛡️ {config['app_name']}</div>
    <div class='sidebar-sub'>Access Key • Keep Ownership</div>
    <div class='sidebar-quote'>“Your keys. Your control. Always offline.”</div>
    <div class='sidebar-divider'></div>
    """,
    unsafe_allow_html=True
)

# --- Sidebar Navigation ---
st.sidebar.header("Navigation")
page = st.sidebar.radio("Navigate to:", ["🔐 Credentials", "🔗 Links"], index=0)

# --- Session setup ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "last_activity" not in st.session_state:
    st.session_state["last_activity"] = datetime.now()

def check_auto_lock():
    if st.session_state["authenticated"]:
        elapsed = datetime.now() - st.session_state["last_activity"]
        if elapsed > timedelta(minutes=AUTO_LOCK_MINUTES):
            st.session_state["authenticated"] = False
            st.session_state.pop("fernet", None)
            st.warning("🔒 Vault locked due to inactivity.")
            st.rerun()

def update_activity():
    st.session_state["last_activity"] = datetime.now()

check_auto_lock()

fernet = None
data = []
links = load_links()

# --- Credentials page ---
if page == "🔐 Credentials":
    if not st.session_state["authenticated"]:
        st.markdown(f"<h2 style='text-align:center;'>🛡️ {config['app_name']}</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; font-size:1.1rem;'>Access Key • Keep Ownership</p>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; font-size:1.1rem;'>“Your keys. Your control. Always offline.”</p>", unsafe_allow_html=True)
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
    data = load_data(fernet)

    if "show_form_creds" not in st.session_state:
        st.session_state["show_form_creds"] = False
    if st.button("➕ Add credential", type="primary"):
        st.session_state["show_form_creds"] = not st.session_state["show_form_creds"]
        update_activity()
    if st.session_state["show_form_creds"]:
        add_credential(data, fernet)
        update_activity()
    show_credentials(data, fernet)
    update_activity()

# --- Links page ---
elif page == "🔗 Links":
    show_links()

# --- Footer ---
st.markdown("---")
st.caption(f"🛡️ {config['app_name']} — Auto-lock after {AUTO_LOCK_MINUTES} min inactivity")
st.caption("💾 credentials.enc → private/ | private_links.json / pro_links.json → separate files")
