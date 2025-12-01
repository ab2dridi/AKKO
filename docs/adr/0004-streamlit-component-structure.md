## Context

The AKKO UI is built with Streamlit. To maintain consistency and reusability, we need a clear structure for components.

## Decision

We structured Streamlit components as follows:
- **Helpers**: Reusable functions like `copy_button` and `find_icon`.
- **Pages**: Separate modules for `credentials_page` and `links_page`.
- **CSS**: Centralized styles in `app.css` and `credentials.css`.

## Consequences

- Contributors must reuse existing helpers instead of duplicating functionality.
- UI changes must align with the defined CSS styles.
