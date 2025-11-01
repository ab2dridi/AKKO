from datetime import date

import streamlit as st

from akko.security import save_data


def add_credential(data, fernet):
    st.subheader("📝 New credential")

    cred_type = st.radio(
        "Credential type",
        ["🌐 Website", "🐧 Linux Server", "🔑 GitLab Token"],
        horizontal=True,
    )

    type_map = {
        "🌐 Website": "Website",
        "🐧 Linux Server": "Linux Server",
        "🔑 GitLab Token": "GitLab Token",
    }

    cred_type = type_map[cred_type]

    with st.form("add_credential", clear_on_submit=True):
        if cred_type == "Website":
            name = st.text_input("Name / Description")
            url = st.text_input("URL")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Add")
            if submitted and name and username and password:
                data.append(
                    {
                        "type": cred_type,
                        "name": name,
                        "url": url,
                        "username": username,
                        "password": password,
                    }
                )
                save_data(data, fernet)
                st.success("✅ Credential added.")

        elif cred_type == "Linux Server":
            hostname = st.text_input("Hostname / IP")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Add")
            if submitted and hostname and username and password:
                data.append(
                    {
                        "type": cred_type,
                        "name": hostname,
                        "hostname": hostname,
                        "username": username,
                        "password": password,
                    }
                )
                save_data(data, fernet)
                st.success("✅ Credential added.")

        else:  # GitLab Token
            name = st.text_input("Token name (e.g. API, CI/CD)")
            token = st.text_input("Personal access token", type="password")

            today = date.today()
            default_date = date(today.year, 12, 31)

            expires = st.checkbox("Token expires?", value=False)
            expiration_date = st.date_input(
                "Expiration date (ignored if unchecked)", value=default_date
            )

            submitted = st.form_submit_button("Add token")
            if submitted and token:
                data.append(
                    {
                        "type": cred_type,
                        "name": name or "GitLab Token",
                        "token": token,
                        "expires": expires,
                        "expiration_date": expiration_date.isoformat()
                        if expires
                        else None,
                    }
                )
                save_data(data, fernet)
                st.success("✅ GitLab token added.")
