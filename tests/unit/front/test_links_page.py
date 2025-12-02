from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

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


def test_render_add_link_toggle_flips_state(mocker: MockerFixture) -> None:
    toggle = cast(Callable[[], None], _get_private("_render_add_link_toggle"))
    session_state: dict[str, object] = {}
    mocker.patch("akko.front.links_page.st.session_state", session_state)
    mocker.patch("akko.front.links_page.st.button", return_value=True)

    toggle()

    assert session_state["show_form_links"] is True


def test_render_filters_returns_expected_values(mocker: MockerFixture) -> None:
    render_filters = cast(
        Callable[[ApplicationData], tuple[str, str, str]],
        _get_private("_render_filters"),
    )
    mocker.patch("akko.front.links_page.st.text_input", return_value="  Query ")
    mocker.patch("akko.front.links_page.st.markdown")
    mocker.patch(
        "akko.front.links_page.st.radio",
        side_effect=["private", "Dev ops"],
    )

    links_data = ApplicationData(
        private=LinkCollection(categories=["dev ops"]),
        public=LinkCollection(),
    )

    query, tag, category = render_filters(links_data)

    assert query == "query"
    assert tag == "private"
    assert category == "dev ops"


def test_render_links_list_invokes_link_card(mocker: MockerFixture) -> None:
    render_list = cast(
        Callable[[list[LinkEntry], ApplicationData], None],
        _get_private("_render_links_list"),
    )
    link = LinkEntry(
        title="Example",
        url=cast(AnyUrl, "https://example.com"),
        category="docs",
    )
    links_data = ApplicationData()
    render_card_mock = mocker.patch("akko.front.links_page._render_link_card")

    render_list([link], links_data)

    render_card_mock.assert_called_once_with(0, link, links_data)


def test_render_link_card_handles_deletion(mocker: MockerFixture) -> None:
    render_card = cast(
        Callable[[int, LinkEntry, ApplicationData], None],
        _get_private("_render_link_card"),
    )
    mocker.patch("akko.front.links_page.find_icon", return_value=None)
    mocker.patch("akko.front.links_page.copy_button")
    mocker.patch("akko.front.links_page.st.markdown")

    columns: list[Any] = []
    for _ in range(4):
        column = mocker.MagicMock()
        column.__enter__.return_value = column
        column.__exit__.return_value = None
        columns.append(column)

    mocker.patch("akko.front.links_page.st.columns", return_value=columns)
    mocker.patch("akko.front.links_page.st.button", return_value=True)
    mocker.patch("akko.front.links_page.save_links")
    mocker.patch("akko.front.links_page.st.success")
    rerun_mock = mocker.patch("akko.front.links_page.st.rerun")
    mocker.patch("akko.front.links_page.st.image")
    mocker.patch("akko.front.links_page.st.code")

    entry = LinkEntry(
        title="Docs",
        url=cast(AnyUrl, "https://docs.example.com"),
        category="docs",
        tag="private",
    )
    links_data = ApplicationData(
        private=LinkCollection(links=[entry], categories=["docs"]),
        public=LinkCollection(),
    )

    render_card(0, entry, links_data)

    assert links_data.private.links == []
    rerun_mock.assert_called_once()


def test_show_links_handles_empty_and_populated(mocker: MockerFixture) -> None:
    mocker.patch("akko.front.links_page.load_links", return_value=ApplicationData())
    mocker.patch("akko.front.links_page.st.subheader")
    info_mock = mocker.patch("akko.front.links_page.st.info")
    mocker.patch("akko.front.links_page._render_add_link_toggle")
    session_state: dict[str, object] = {"show_form_links": False}
    mocker.patch("akko.front.links_page.st.session_state", session_state)

    links_page.show_links()

    info_mock.assert_called_once()

    populated = ApplicationData(
        private=LinkCollection(
            links=[
                LinkEntry(
                    title="Docs",
                    url=cast(AnyUrl, "https://docs.example.com"),
                    category="docs",
                    tag="private",
                )
            ],
            categories=["docs"],
        )
    )

    mocker.patch("akko.front.links_page.load_links", return_value=populated)
    mocker.patch("akko.front.links_page._render_add_link_toggle")
    mocker.patch("akko.front.links_page._render_add_link_form")
    mocker.patch(
        "akko.front.links_page._render_filters",
        return_value=("", "All", "All"),
    )
    render_list_mock = mocker.patch("akko.front.links_page._render_links_list")
    warning_mock = mocker.patch("akko.front.links_page.st.warning")

    links_page.show_links()

    render_list_mock.assert_called_once()
    warning_mock.assert_not_called()
