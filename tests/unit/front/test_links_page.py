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


def test_format_category_option_labels_new_choice() -> None:
    format_category_option = cast(
        Callable[[object], str],
        _get_private("_format_category_option"),
    )
    new_category_option = _get_private("_NEW_CATEGORY_OPTION")

    assert format_category_option(new_category_option) == "(New category)"
    assert format_category_option("docs") == "Docs"


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
