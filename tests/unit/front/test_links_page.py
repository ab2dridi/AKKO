from __future__ import annotations

from collections.abc import Callable
from typing import cast

from pydantic import AnyUrl
from pytest_mock import MockerFixture

import akko.front.links_page as links_page
from akko.typing.security import ApplicationData, LinkCollection, LinkEntry


def _get_private(name: str) -> object:
    return getattr(links_page, name)


def test_normalize_category_trims_and_lowercases() -> None:
    normalize_category = cast(Callable[[str], str], _get_private("_normalize_category"))
    assert normalize_category("  Dev Ops  ") == "dev ops"


def test_display_category_capitalizes() -> None:
    display_category = cast(Callable[[str], str], _get_private("_display_category"))
    assert display_category("dev ops") == "Dev ops"
    assert display_category("") == "Other"


def test_filter_links_applies_filters() -> None:
    links_data = ApplicationData(
        private=LinkCollection(
            categories=["internal"],
            links=[
                LinkEntry(
                    title="Private Docs",
                    url=cast(AnyUrl, "https://internal.example.com"),
                    category="internal",
                    tag="private",
                )
            ],
        ),
        public=LinkCollection(
            categories=["news"],
            links=[
                LinkEntry(
                    title="Public News",
                    url=cast(AnyUrl, "https://news.example.com"),
                    category="news",
                    tag="public",
                )
            ],
        ),
    )

    filter_links = cast(
        Callable[[ApplicationData, str, str, str], list[LinkEntry]],
        _get_private("_filter_links"),
    )

    filtered = filter_links(links_data, "news", "public", "All")

    assert len(filtered) == 1
    assert filtered[0].title == "Public News"

    filtered = filter_links(links_data, "", "private", "All")
    assert len(filtered) == 1
    assert filtered[0].title == "Private Docs"

    filtered = filter_links(links_data, "", "All", "news")
    assert len(filtered) == 1
    assert filtered[0].title == "Public News"


def test_add_link_rejects_invalid_tag(mocker: MockerFixture) -> None:
    links_data = ApplicationData()
    error_mock = mocker.patch("akko.front.links_page.st.error")
    save_mock = mocker.patch("akko.front.links_page.save_links")

    add_link = cast(
        Callable[[ApplicationData, str, str, str, str], None],
        _get_private("_add_link"),
    )

    add_link(links_data, "Title", "https://example.com", "docs", "secret")

    error_mock.assert_called_once_with("Invalid visibility tag selected.")
    save_mock.assert_not_called()


def test_add_link_appends_and_persists(mocker: MockerFixture) -> None:
    links_data = ApplicationData()
    session_state: dict[str, object] = {"show_form_links": True}
    mocker.patch("akko.front.links_page.st.session_state", session_state)
    mocker.patch("akko.front.links_page.st.error")
    success_mock = mocker.patch("akko.front.links_page.st.success")
    rerun_mock = mocker.patch("akko.front.links_page.st.rerun")
    save_mock = mocker.patch("akko.front.links_page.save_links")

    add_link = cast(
        Callable[[ApplicationData, str, str, str, str], None],
        _get_private("_add_link"),
    )

    add_link(links_data, "Docs", "https://docs.example.com", "docs", "private")

    assert links_data.private.links[0].title == "Docs"
    assert "docs" in links_data.private.categories
    save_mock.assert_called_once_with(links_data)
    success_mock.assert_called_once()
    assert session_state["show_form_links"] is False
    rerun_mock.assert_called_once()


def test_add_link_handles_invalid_url(mocker: MockerFixture) -> None:
    links_data = ApplicationData()
    error_mock = mocker.patch("akko.front.links_page.st.error")
    save_mock = mocker.patch("akko.front.links_page.save_links")

    add_link = cast(
        Callable[[ApplicationData, str, str, str, str], None],
        _get_private("_add_link"),
    )

    add_link(links_data, "Title", "not-a-valid-url", "docs", "public")

    error_mock.assert_called_once()
    assert "Invalid URL" in str(error_mock.call_args[0][0])
    save_mock.assert_not_called()


def test_add_link_for_public_tag(mocker: MockerFixture) -> None:
    links_data = ApplicationData()
    session_state: dict[str, object] = {"show_form_links": True}
    mocker.patch("akko.front.links_page.st.session_state", session_state)
    mocker.patch("akko.front.links_page.st.success")
    mocker.patch("akko.front.links_page.st.rerun")
    save_mock = mocker.patch("akko.front.links_page.save_links")

    add_link = cast(
        Callable[[ApplicationData, str, str, str, str], None],
        _get_private("_add_link"),
    )

    add_link(links_data, "Blog", "https://blog.example.com", "news", "public")

    assert len(links_data.public.links) == 1
    assert links_data.public.links[0].title == "Blog"
    assert "news" in links_data.public.categories
    save_mock.assert_called_once()


def test_add_link_skips_existing_category(mocker: MockerFixture) -> None:
    links_data = ApplicationData(public=LinkCollection(categories=["docs"], links=[]))
    session_state: dict[str, object] = {"show_form_links": True}
    mocker.patch("akko.front.links_page.st.session_state", session_state)
    mocker.patch("akko.front.links_page.st.success")
    mocker.patch("akko.front.links_page.st.rerun")
    mocker.patch("akko.front.links_page.save_links")

    add_link = cast(
        Callable[[ApplicationData, str, str, str, str], None],
        _get_private("_add_link"),
    )

    add_link(links_data, "Guide", "https://guide.example.com", "docs", "public")

    # La catégorie "docs" ne doit pas être dupliquée
    assert links_data.public.categories.count("docs") == 1


def test_filter_links_by_category() -> None:
    links_data = ApplicationData(
        public=LinkCollection(
            categories=["docs", "news"],
            links=[
                LinkEntry(
                    title="Documentation",
                    url=cast(AnyUrl, "https://docs.example.com"),
                    category="docs",
                    tag="public",
                ),
                LinkEntry(
                    title="News",
                    url=cast(AnyUrl, "https://news.example.com"),
                    category="news",
                    tag="public",
                ),
            ],
        ),
    )

    filter_links = cast(
        Callable[[ApplicationData, str, str, str], list[LinkEntry]],
        _get_private("_filter_links"),
    )

    # Filtrer par catégorie "docs"
    filtered = filter_links(links_data, "", "All", "docs")
    assert len(filtered) == 1
    assert filtered[0].title == "Documentation"


def test_filter_links_by_query() -> None:
    links_data = ApplicationData(
        public=LinkCollection(
            categories=["docs"],
            links=[
                LinkEntry(
                    title="Python Documentation",
                    url=cast(AnyUrl, "https://python.org"),
                    category="docs",
                    tag="public",
                ),
                LinkEntry(
                    title="JavaScript Guide",
                    url=cast(AnyUrl, "https://javascript.com"),
                    category="docs",
                    tag="public",
                ),
            ],
        ),
    )

    filter_links = cast(
        Callable[[ApplicationData, str, str, str], list[LinkEntry]],
        _get_private("_filter_links"),
    )

    # Recherche par titre
    filtered = filter_links(links_data, "python", "All", "All")
    assert len(filtered) == 1
    assert filtered[0].title == "Python Documentation"

    # Recherche par URL
    filtered = filter_links(links_data, "javascript.com", "All", "All")
    assert len(filtered) == 1
    assert filtered[0].title == "JavaScript Guide"

    # Recherche par catégorie dans la query
    filtered = filter_links(links_data, "docs", "All", "All")
    assert len(filtered) == 2


def test_render_add_link_toggle(mocker: MockerFixture) -> None:
    session_state: dict[str, object] = {}
    mocker.patch("akko.front.links_page.st.session_state", session_state)
    button_mock = mocker.patch("akko.front.links_page.st.button", return_value=False)

    render_toggle = cast(Callable[[], None], _get_private("_render_add_link_toggle"))
    render_toggle()

    # Vérifie que l'état par défaut est False
    assert session_state["show_form_links"] is False
    button_mock.assert_called_once()


def test_render_add_link_toggle_switches_state(mocker: MockerFixture) -> None:
    session_state: dict[str, object] = {"show_form_links": False}
    mocker.patch("akko.front.links_page.st.session_state", session_state)
    mocker.patch("akko.front.links_page.st.button", return_value=True)

    render_toggle = cast(Callable[[], None], _get_private("_render_add_link_toggle"))
    render_toggle()

    # L'état devrait être inversé
    assert session_state["show_form_links"] is True
