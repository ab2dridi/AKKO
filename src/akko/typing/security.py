from __future__ import annotations

from pydantic import AnyUrl, BaseModel, Field, model_validator


class LinkEntry(BaseModel):
    """Link entry stored on disk or used in the UI.

    Attributes:
        title (str): Title of the link.
        url (AnyUrl): Fully qualified URL associated with the link.
        category (str): Category assigned to the link.
        tag (str): Tag indicating whether the link is public or private.
    """

    title: str = Field(default="(Untitled)", description="Title of the link")
    url: AnyUrl = Field(
        default=AnyUrl("https://someurl.com"), description="URL of the link"
    )
    category: str = Field(default="other", description="Category of the link")
    tag: str = Field(
        default="public", description="Tag indicating public or private link"
    )

    def __getitem__(self, name: str) -> object:
        """Get item by attributes name.

        Args:
            name (str): The name of the attribute to retrieve.

        Returns:
            object: The value of the attribute.
        """
        return super().__getattribute__(name)

    def get(self, name: str) -> object | None:
        """Get item by attributes name.

        Args:
            name (str): The name of the attribute to retrieve.

        Returns:
            object | None: The value of the attribute or None if not found.
        """
        try:
            return self.__getitem__(name)
        except AttributeError:
            return None


class LinkCollection(BaseModel):
    """Collection of links with associated categories.

    Attributes:
        categories (list[str]): List of link categories.
        links (list[LinkEntry]): List of link entries in the collection.
    """

    categories: list[str] = Field(
        default_factory=list[str], description="List of link categories"
    )
    links: list[LinkEntry] = Field(
        default_factory=list[LinkEntry], description="List of link entries"
    )

    def __getitem__(self, name: str) -> str | AnyUrl:
        """Get item by attributes name.

        Args:
            name (str): The name of the attribute to retrieve.

        Returns:
            str | AnyUrl: The value of the attribute.
        """
        return super().__getattribute__(name)  # type: ignore[no-any-return]

    def get(self, name: str) -> str | AnyUrl | None:
        """Get item by attributes name.

        Args:
            name (str): The name of the attribute to retrieve.

        Returns:
            str | AnyUrl | None: The value of the attribute or None if not found.
        """
        try:
            return self.__getitem__(name)
        except AttributeError:
            return None


class ApplicationData(BaseModel):
    """Application data structure containing private and public link groups.

    Attributes:
        private (LinkCollection): Collection of private links.
        public (LinkCollection): Collection of public links.
    """

    private: LinkCollection = Field(
        default_factory=LinkCollection, description="Collection of private links"
    )
    public: LinkCollection = Field(
        default_factory=LinkCollection, description="Collection of public links"
    )

    def __getitem__(self, name: str) -> LinkCollection:
        """Get item by attributes name.

        Args:
            name (str): The name of the attribute to retrieve.

        Returns:
            LinkCollection: The value of the attribute.
        """
        result = super().__getattribute__(name)
        if not isinstance(result, LinkCollection):
            raise KeyError(f"No such attribute: {name}")
        return result

    def get(self, name: str) -> LinkCollection:
        """Get item by attributes name.

        Args:
            name (str): The name of the attribute to retrieve.

        Returns:
            LinkCollection: The value of the attribute.
        """
        try:
            return self.__getitem__(name)
        except (KeyError, AttributeError):
            return LinkCollection()

    @model_validator(mode="after")
    def _ensure_tag_in_links(self) -> ApplicationData:
        """Ensure that all links have a tag."""
        for link in self.private.links:
            link.tag = "private"
        for link in self.public.links:
            link.tag = "public"
        return self

    def all_categories(self) -> list[str]:
        """Get all unique categories from both link collections.

        Returns:
            list[str]: Sorted list of all unique, normalized categories.
        """

        def _norm(s: object) -> str:
            return str(s).strip().lower()

        explicit = {
            _norm(category)
            for collection in (self.private, self.public)
            for category in collection.categories
        }
        from_links = {
            _norm(link.category)
            for collection in (self.private, self.public)
            for link in collection.links
            if getattr(link, "category", None)
        }
        return sorted(explicit | from_links)

    def all_links(self) -> list[LinkEntry]:
        """Get all links from both link collections.

        Returns:
            list[LinkEntry]: A list of all link entries.
        """
        return self.private.links + self.public.links
