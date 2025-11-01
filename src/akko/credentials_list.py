import streamlit as st
from utils.helpers import try_copy
from utils.security import save_data
from datetime import datetime


def show_credentials(data, fernet):
    st.subheader("📂 Your credentials")

    if not data:
        st.info("No credentials stored yet.")
        return

    # --- Search ---
    query = st.text_input("🔎 Quick search (name, URL, user, host...)", "").strip().lower()

    # --- Filter by type ---
    st.markdown("### 🔍 Filter by type")
    types = ["🌐 Websites", "🐧 Linux Servers", "🔑 GitLab Tokens", "All"]
    type_map = {
        "🌐 Websites": "Website",
        "🐧 Linux Servers": "Linux Server",
        "🔑 GitLab Tokens": "GitLab Token"
    }
    selected_type = st.radio("", types, horizontal=True, index=3)

    filtered = data if selected_type == "All" else [
        d for d in data if d.get("type") == type_map[selected_type]
    ]

    # --- Apply search ---
    if query:
        filtered = [
            d for d in filtered
            if query in str(d.get("name", "")).lower()
            or query in str(d.get("url", "")).lower()
            or query in str(d.get("username", "")).lower()
            or query in str(d.get("hostname", "")).lower()
            or query in str(d.get("token", "")).lower()
        ]

    if not filtered:
        st.warning("No credentials match your search.")
        return

    # --- Global card style ---
    st.markdown("""
        <style>
            .akko-card {
                background: rgba(255, 255, 255, 0.8);
                border-radius: 14px;
                padding: 1rem 1.2rem;
                margin-bottom: 1rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                transition: all 0.2s ease-in-out;
            }
            .akko-card:hover {
                transform: scale(1.01);
                box-shadow: 0 6px 16px rgba(0,0,0,0.08);
            }
            .akko-title {
                font-weight: 600;
                font-size: 1.05rem;
            }
            .akko-sub {
                color: #777;
                font-size: 0.9rem;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- Display each credential as a card ---
    for idx, item in enumerate(filtered):
        icon = (
            "🌐" if item.get("type") == "Website"
            else "🐧" if item.get("type") == "Linux Server"
            else "🔑"
        )

        name = item.get("name", "(no name)")
        cred_type = item.get("type", "")

        # Header
        st.markdown(f"""
        <div class="akko-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:1.2rem;">{icon}</span>
                    <span class="akko-title" style="margin-left:8px;">{name}</span>
                    <span class="akko-sub" style="margin-left:10px;">({cred_type})</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- Details by type ---
        cols = st.columns([3, 3, 3, 2])

        # --- WEBSITE ---
        if cred_type == "Website":
            with cols[0]:
                url = item.get("url") or ""
                st.write("**URL:**")
                if url:
                    st.markdown(f"[🌐 Open link]({url})", unsafe_allow_html=True)
                st.code(url, language="")
                if st.button("📋 Copy URL", key=f"url_{idx}"):
                    try_copy(url, "URL")

            with cols[1]:
                st.write("**Username:**")
                st.code(item.get("username") or "", language="")
                if st.button("📋 Copy username", key=f"user_{idx}"):
                    try_copy(item.get("username") or "", "Username")

            with cols[2]:
                st.write("**Password:**")
                show = st.checkbox("Show", key=f"show_{idx}")
                st.code(item.get("password") if show else "•" * 8, language="")
                if st.button("📋 Copy password", key=f"pass_{idx}"):
                    try_copy(item.get("password") or "", "Password")

        # --- LINUX SERVER ---
        elif cred_type == "Linux Server":
            with cols[0]:
                st.write("**Hostname / IP:**")
                st.code(item.get("hostname") or "", language="")
                if st.button("📋 Copy host", key=f"host_{idx}"):
                    try_copy(item.get("hostname") or "", "Hostname")

            with cols[1]:
                st.write("**Username:**")
                st.code(item.get("username") or "", language="")
                if st.button("📋 Copy username", key=f"user_{idx}"):
                    try_copy(item.get("username") or "", "Username")

            with cols[2]:
                st.write("**Password:**")
                show = st.checkbox("Show", key=f"show_{idx}")
                st.code(item.get("password") if show else "•" * 8, language="")
                if st.button("📋 Copy password", key=f"pass_{idx}"):
                    try_copy(item.get("password") or "", "Password")

        # --- GITLAB TOKEN ---
        elif cred_type == "GitLab Token":
            with cols[0]:
                st.write("**Token:**")
                show = st.checkbox("Show", key=f"show_token_{idx}")
                st.code(item.get("token") if show else "•" * 12, language="")
                if st.button("📋 Copy token", key=f"token_{idx}"):
                    try_copy(item.get("token") or "", "GitLab Token")

            with cols[1]:
                expires = item.get("expires", False)
                exp_date = item.get("expiration_date")
                if expires and exp_date:
                    try:
                        exp_date_obj = datetime.fromisoformat(exp_date)
                        remaining_days = (exp_date_obj - datetime.now()).days
                        if remaining_days < 0:
                            st.error(f"⛔ Expired {abs(remaining_days)} days ago.")
                        elif remaining_days <= 7:
                            st.warning(f"⚠️ Expires in {remaining_days} days.")
                        else:
                            st.success(f"✅ Valid ({remaining_days} days left).")
                    except Exception:
                        st.error("Error reading expiration date.")
                else:
                    st.info("🔒 Token without expiration.")

        # --- Delete button ---
        with cols[3]:
            if st.button("🗑️ Delete", key=f"del_{idx}"):
                data.remove(item)
                save_data(data, fernet)
                st.success("✅ Credential deleted.")
                st.rerun()

        # Close card div
        st.markdown("</div>", unsafe_allow_html=True)
