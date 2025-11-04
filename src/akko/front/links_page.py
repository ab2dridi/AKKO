"""Streamlit page responsible for displaying, filtering, and managing links."""

from typing import cast

import streamlit as st
from pydantic import AnyUrl, ValidationError

from akko.core.security import load_links, save_links
from akko.front.helpers import find_icon, try_copy
from akko.typing.security import ApplicationData, LinkCollection, LinkEntry


def _normalize_category(name: str) -> str:
    """Normalize category name to lowercase.

    Args:
        name (str): The category name to normalize.

    Returns:
        str: The normalized category name.
    """
    return name.strip().lower()


def _display_category(name: str) -> str:
    """Display category name with proper capitalization.

    Args:
        name (str): The category name to display.

    Returns:
        str: The displayed category name.
    """
    return name.strip().capitalize() if name else "Other"


_NEW_CATEGORY_OPTION = object()


def _format_category_option(option: object) -> str:
    """Format category options for the select box display.

    Args:
        option (object): Raw option returned by the select box.

    Returns:
        str: User-friendly label rendered in the UI.

    """
    if option == _NEW_CATEGORY_OPTION:
        return "(New category)"
    return _display_category(cast(str, option))


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

    with st.form("add_link", clear_on_submit=True):
        title = st.text_input("Title")
        url = st.text_input("URL")

        cat_col = st.columns([2, 1])
        category_options: list[object] = [
            _NEW_CATEGORY_OPTION,
            *links_data.all_categories(),
        ]
        with cat_col[0]:
            category_choice = st.selectbox(
                "Category",
                category_options,
                format_func=_format_category_option,
            )
        with cat_col[1]:
            new_cat = (
                st.text_input("New category")
                if category_choice == _NEW_CATEGORY_OPTION
                else ""
            )

        tag = st.radio("Visibility", ["public", "private"], horizontal=True)
        submitted = st.form_submit_button("Add")

    if submitted and title and url:
        if category_choice == _NEW_CATEGORY_OPTION:
            final_cat = _normalize_category(new_cat)
        else:
            final_cat = _normalize_category(cast(str, category_choice))

        if not final_cat:
            st.error("Please provide a category name.")
            return

        _add_link(links_data, title.strip(), url.strip(), final_cat, tag)


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
        if st.button("📋 Copy URL", key=f"copy_{idx}"):
            try_copy(url, "URL")
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
