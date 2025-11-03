from __future__ import annotations

from typing import cast

import pytest
from pydantic import AnyUrl

from akko.typing.security import ApplicationData, LinkCollection, LinkEntry


def test_link_entry_getitem_returns_attribute() -> None:
    entry = LinkEntry(
        title="Example",
        url=cast(AnyUrl, "https://example.com/resource"),
        category="news",
        tag="public",
    )

    assert entry["title"] == "Example"
    assert str(entry["url"]) == "https://example.com/resource"


def test_link_entry_get_returns_none_for_unknown_field() -> None:
    entry = LinkEntry(
        title="Example",
        url=cast(AnyUrl, "https://example.com"),
        category="news",
    )

    assert entry.get("missing") is None


def test_link_collection_getitem_returns_attribute() -> None:
    entry = LinkEntry(
        title="Example",
        url=cast(AnyUrl, "https://example.com"),
        category="news",
    )
    collection = LinkCollection(categories=["news"], links=[entry])

    assert collection["categories"] == ["news"]
    assert collection["links"] == [entry]


def test_link_collection_get_returns_none_for_unknown_field() -> None:
    collection = LinkCollection()

    assert collection.get("missing") is None


def test_application_data_getitem_returns_link_collection() -> None:
    app_data = ApplicationData()

    assert isinstance(app_data["private"], LinkCollection)
    assert isinstance(app_data["public"], LinkCollection)


def test_application_data_getitem_raises_for_non_collection() -> None:
    app_data = ApplicationData()
    object.__setattr__(app_data, "private", "not-a-collection")

    with pytest.raises(KeyError):
        _ = app_data["private"]


def test_application_data_get_returns_empty_collection_when_missing() -> None:
    app_data = ApplicationData()

    collection = app_data.get("missing")

    assert isinstance(collection, LinkCollection)
    assert collection.links == []
    assert collection.categories == []


def test_application_data_get_returns_empty_collection_when_invalid() -> None:
    app_data = ApplicationData()
    object.__setattr__(app_data, "private", "not-a-collection")

    collection = app_data.get("private")

    assert isinstance(collection, LinkCollection)
    assert collection.links == []
    assert collection.categories == []


def test_application_data_sets_tags_via_validator() -> None:
    private_entry = LinkEntry(
        title="Private",
        url=cast(AnyUrl, "https://private.example.com"),
        category="infra",
        tag="public",
    )
    public_entry = LinkEntry(
        title="Public",
        url=cast(AnyUrl, "https://public.example.com"),
        category="docs",
        tag="private",
    )
    app_data = ApplicationData(
        private=LinkCollection(links=[private_entry]),
        public=LinkCollection(links=[public_entry]),
    )

    assert app_data.private.links[0].tag == "private"
    assert app_data.public.links[0].tag == "public"


def test_application_data_all_categories_returns_sorted_unique() -> None:
    app_data = ApplicationData(
        private=LinkCollection(categories=["infra", "ops", "general"]),
        public=LinkCollection(categories=["general", "docs"]),
    )

    assert app_data.all_categories() == ["docs", "general", "infra", "ops"]


def test_application_data_all_links_combines_collections() -> None:
    private_links = [
        LinkEntry(
            title="Private A",
            url=cast(AnyUrl, "https://a.example.com"),
            category="infra",
        ),
        LinkEntry(
            title="Private B",
            url=cast(AnyUrl, "https://b.example.com"),
            category="ops",
        ),
    ]
    public_links = [
        LinkEntry(
            title="Public",
            url=cast(AnyUrl, "https://c.example.com"),
            category="docs",
        ),
    ]
    app_data = ApplicationData(
        private=LinkCollection(links=private_links),
        public=LinkCollection(links=public_links),
    )

    all_links = app_data.all_links()

    assert all_links == private_links + public_links
