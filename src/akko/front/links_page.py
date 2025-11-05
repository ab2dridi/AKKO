"""Streamlit page responsible for displaying, filtering, and managing links."""

import unicodedata

import streamlit as st
from pydantic import AnyUrl, ValidationError

from akko.core.security import load_links, save_links
from akko.front.helpers import copy_button, find_icon
from akko.typing.security import ApplicationData, LinkCollection, LinkEntry

ADD_NEW_CATEGORY_LABEL = "add New category"
_NEW_CATEGORY_OPTION = object()
NEW_CATEGORY_LABEL = "(New category)"


def _normalize_category(name: str) -> str:
    """Normalize category name to lowercase.

    Args:
        name (str): The category name to normalize.

    Returns:
        str: The normalized category name.
    """
    s = unicodedata.normalize("NFKC", name or "").strip().lower()
    return " ".join(s.split())


def _display_category(name: str) -> str:
    """Display category name with proper capitalization.

    Args:
        name (str): The category name to display.

    Returns:
        str: The displayed category name.
    """
    return name.strip().capitalize() if name else "Other"


def _render_add_link_toggle() -> None:
    """Render the toggle button that expands or collapses the link form."""
    st.session_state["show_form_links"] = st.session_state.get("show_form_links", False)
    if st.button("Toggle add link", type="primary"):
        st.session_state["show_form_links"] = not st.session_state["show_form_links"]


def _render_add_link_form(links_data: ApplicationData) -> None:
    """Render the form used to capture link metadata and handle submission.

    Args:
        links_data (ApplicationData): Mutable application data storing the links.
    """
    st.markdown("### 📝 New link")

    categories = sorted(
        {
            _normalize_category(c)
            for c in links_data.all_categories()
            if (c or "").strip()
        }
    )
    options = [NEW_CATEGORY_LABEL, *list(categories)]
    cat_col = st.columns([2, 1], vertical_alignment="center")
    with cat_col[0]:
        category_choice: str = st.selectbox(
            "Category",
            options,
            index=0,
            key="addlink_category_choice",
        )

    with cat_col[1]:
        new_cat_val = st.text_input(
            "New category",
            key="addlink_new_cat_input",
            disabled=(category_choice != NEW_CATEGORY_LABEL),
            placeholder="e.g. tutorials",
        ).strip()

    with st.form("add_link", clear_on_submit=True):
        title = st.text_input("Title", key="addlink_title")
        url = st.text_input("URL", key="addlink_url")
        _ = st.radio(
            "Visibility", ["public", "private"], horizontal=True, key="addlink_tag"
        )
        submitted = st.form_submit_button("Add")

    if not submitted:
        return

    if category_choice == NEW_CATEGORY_LABEL:
        final_cat = _normalize_category(new_cat_val)
    else:
        final_cat = _normalize_category(category_choice)

    if not title or not url:
        st.error("Please provide both a title and an URL.")
        return
    if not final_cat:
        st.error("Please provide a category name.")
        return

    _add_link(
        links_data,
        title.strip(),
        url.strip(),
        final_cat,
        st.session_state["addlink_tag"],
    )


def _add_link(
    links_data: ApplicationData, title: str, url: str, final_cat: str, tag: str
) -> None:
    """Persist a new link entry and refresh the UI.

    Args:
        links_data (ApplicationData): Collection holding public and private links.
        title (str): Human friendly title for the link.
        url (str): URL string provided by the user.
        final_cat (str): Normalized category assigned to the link.
        tag (str): Visibility selector, ``public`` or ``private``.
    """
    if tag not in ("public", "private"):
        st.error("Invalid visibility tag selected.")
        return

    tag_group: LinkCollection = links_data.get(tag)

    if final_cat and final_cat not in tag_group.categories:
        tag_group.categories.append(final_cat)

    try:
        tag_group.links.append(
            LinkEntry(title=title, url=AnyUrl(url), category=final_cat, tag=tag)
        )
    except ValidationError as exc:
        st.error(f"Invalid URL: {exc}")
        return

    save_links(links_data)
    st.success("✅ Link added successfully.")
    st.session_state["show_form_links"] = False
    st.rerun()


def _render_filters(links_data: ApplicationData) -> tuple[str, str, str]:
    """Render filters and return the chosen query and visibility constraints.

    Args:
        links_data (ApplicationData): Collection used to populate filter choices.

    Returns:
        tuple[str, str, str]: A triple containing the search query, selected
            visibility tag, and normalized category filter.
    """
    query = st.text_input("🔎 Search (title, URL, category)").strip().lower()

    st.markdown("### 🔍 Filters")
    filter_tag = st.radio(
        "Visibility", ["All", "public", "private"], horizontal=True, index=0
    )

    display_cats = [_display_category(c) for c in links_data.all_categories()]
    filter_cat_display = st.radio(
        "Category", ["All", *display_cats], horizontal=True, index=0
    )
    filter_cat = (
        _normalize_category(filter_cat_display)
        if filter_cat_display != "All"
        else "All"
    )

    return query, filter_tag, filter_cat


def _filter_links(
    links_data: ApplicationData, query: str, filter_tag: str, filter_cat: str
) -> list[LinkEntry]:
    """Filter links according to the provided search query and filters.

    Args:
        links_data (ApplicationData): Source collection containing all links.
        query (str): Lowercase search text applied across title, URL, and category.
        filter_tag (str): Visibility filter (``All``, ``public``, or ``private``).
        filter_cat (str): Normalized category name or ``All`` for no filtering.

    Returns:
        list[LinkEntry]: Filtered list respecting the requested criteria.
    """
    filtered: list[LinkEntry] = []
    for link in links_data.all_links():
        if filter_tag != "All" and link.tag != filter_tag:
            continue
        if (
            filter_cat != "All"
            and _normalize_category(str(link.category)) != filter_cat
        ):
            continue
        filtered.append(link)

    if query:
        filtered = [
            link
            for link in filtered
            if query in link.title.lower()
            or query in str(link.url).lower()
            or query in _normalize_category(str(link.category))
        ]

    return filtered


def _render_links_list(
    filtered_links: list[LinkEntry], links_data: ApplicationData
) -> None:
    """Render the list of filtered links using individual cards.

    Args:
        filtered_links (list[LinkEntry]): Subset of links that passed filtering.
        links_data (ApplicationData): Collection used for subsequent updates.
    """
    for idx, link in enumerate(filtered_links):
        _render_link_card(idx, link, links_data)


def _render_link_card(idx: int, link: LinkEntry, links_data: ApplicationData) -> None:
    """Render a single link card with actions for copy and deletion.

    Args:
        idx (int): Unique index used for Streamlit widget keys.
        link (LinkEntry): Link metadata to render.
        links_data (ApplicationData): Collection updated when deletion occurs.
    """
    icon_file = find_icon(str(link.category))
    title = link.title.strip()
    url = str(link.url).strip()
    cat = _display_category(str(link.category))
    tag = link.tag

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
        if icon_file and icon_file.exists():
            st.image(str(icon_file), width=40)
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
        copy_button(url, "📋 Copy URL")
        st.markdown(f"Category: *{cat}*")

    with cols[2]:
        st.markdown(f"🏷️ *{tag}*")

    with cols[3]:
        if st.button("🗑️", key=f"del_{idx}"):
            try:
                collection: LinkCollection = links_data.get(tag)
                collection.links.remove(link)
                save_links(links_data)
                st.success(f"✅ Link '{title}' deleted.")
                st.rerun()
            except Exception as e:  # pragma: no cover - user feedback path
                st.error(f"Error while deleting: {e}")

    st.markdown("</div>", unsafe_allow_html=True)


def show_links() -> None:
    """Entry point that displays links and orchestrates user interactions."""
    links_data = load_links()

    st.subheader("🌐 Links")

    _render_add_link_toggle()

    if st.session_state["show_form_links"]:
        _render_add_link_form(links_data)

    if not links_data.all_links():
        st.info("No links recorded yet.")
        return

    query, filter_tag, filter_cat = _render_filters(links_data)
    filtered_links = _filter_links(links_data, query, filter_tag, filter_cat)

    if not filtered_links:
        st.warning("No matching links found.")
        return

    _render_links_list(filtered_links, links_data)
