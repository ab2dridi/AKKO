import os

import streamlit as st

from akko.helpers import find_icon, try_copy
from akko.security import load_links, save_links


def normalize_category(name: str) -> str:
    return name.strip().lower()


def display_category(name: str) -> str:
    return name.strip().capitalize() if name else "Other"


def show_links():
    links_data = load_links()
    private_links = links_data["perso"]
    public_links = links_data["pro"]

    all_links = []
    for tag, data in [("private", private_links), ("public", public_links)]:
        for l in data["links"]:
            l["_tag"] = tag
        all_links.extend(data["links"])

    all_categories = sorted(
        list(
            set(
                normalize_category(c)
                for d in [private_links, public_links]
                for c in d["categories"]
            )
        )
    )

    st.subheader("🌐 Links")

    # --- Add link form toggle ---
    if "show_form_links" not in st.session_state:
        st.session_state["show_form_links"] = False

    if st.button("➕ Add link", type="primary"):
        st.session_state["show_form_links"] = not st.session_state["show_form_links"]

    # --- Add link form ---
    if st.session_state["show_form_links"]:
        st.markdown("### 📝 New link")

        with st.form("add_link", clear_on_submit=True):
            title = st.text_input("Title")
            url = st.text_input("URL")

            cat_col = st.columns([2, 1])
            with cat_col[0]:
                display_cats = [display_category(c) for c in all_categories]
                category_display = st.selectbox(
                    "Existing category", ["(New category)"] + display_cats
                )
            with cat_col[1]:
                new_cat = (
                    st.text_input("New category")
                    if category_display == "(New category)"
                    else ""
                )

            tag = st.radio("Visibility", ["public", "private"], horizontal=True)
            submitted = st.form_submit_button("Add")

            if submitted and title and url:
                final_cat = normalize_category(new_cat or category_display)
                target = public_links if tag == "public" else private_links

                if final_cat and final_cat not in target["categories"]:
                    target["categories"].append(final_cat)

                target["links"].append(
                    {"title": title, "url": url, "category": final_cat}
                )

                save_links({"perso": private_links, "pro": public_links})
                st.success("✅ Link added successfully.")
                st.session_state["show_form_links"] = False
                st.rerun()

    # --- Display links ---
    if all_links:
        query = st.text_input("🔎 Search (title, URL, category)").strip().lower()

        st.markdown("### 🔍 Filters")
        filter_tag = st.radio(
            "Visibility", ["All", "public", "private"], horizontal=True, index=0
        )

        display_cats = [display_category(c) for c in all_categories]
        filter_cat_display = st.radio(
            "Category", ["All"] + display_cats, horizontal=True, index=0
        )
        filter_cat = (
            normalize_category(filter_cat_display)
            if filter_cat_display != "All"
            else "All"
        )

        filtered = [
            l
            for l in all_links
            if (filter_tag == "All" or l["_tag"] == filter_tag)
            and (filter_cat == "All" or normalize_category(l["category"]) == filter_cat)
        ]

        if query:
            filtered = [
                l
                for l in filtered
                if query in l.get("title", "").lower()
                or query in l.get("url", "").lower()
                or query in normalize_category(l.get("category", ""))
            ]

        if not filtered:
            st.warning("No matching links found.")
        else:
            for idx, l in enumerate(filtered):
                icon_file = find_icon(l.get("category", ""))
                title = l.get("title", "").strip() or "(Untitled)"
                url = l.get("url", "").strip()
                cat = display_category(l.get("category", ""))
                tag = l.get("_tag", "public")

                # --- Card-style block ---
                st.markdown(
                    """
                    <div style="background:rgba(255,255,255,0.8);
                                border-radius:14px;
                                padding:1rem 1.2rem;
                                margin-bottom:1rem;
                                box-shadow:0 4px 12px rgba(0,0,0,0.05);
                                transition:all 0.2s ease-in-out;">
                """,
                    unsafe_allow_html=True,
                )

                cols = st.columns([1.2, 6, 2, 1])
                with cols[0]:
                    if icon_file and os.path.exists(icon_file):
                        st.image(icon_file, width=40)
                    else:
                        st.markdown(
                            "<div style='font-size:28px;'>🗂️</div>",
                            unsafe_allow_html=True,
                        )

                with cols[1]:
                    st.markdown(f"**{title}**")
                    if url:
                        st.markdown(f"[🌐 Open link]({url})", unsafe_allow_html=True)
                    st.code(url or "", language="")
                    if st.button("📋 Copy URL", key=f"copy_{idx}"):
                        try_copy(url, "URL")
                    st.markdown(f"Category: *{cat}*")

                with cols[2]:
                    st.markdown(f"🏷️ *{tag}*")

                with cols[3]:
                    if st.button("🗑️", key=f"del_{idx}"):
                        try:
                            if tag == "public":
                                public_links["links"].remove(l)
                            else:
                                private_links["links"].remove(l)
                            save_links({"perso": private_links, "pro": public_links})
                            st.success(f"✅ Link '{title}' deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error while deleting: {e}")

                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No links recorded yet.")
