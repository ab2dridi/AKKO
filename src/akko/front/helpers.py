from pathlib import Path

import pyperclip
import streamlit as st
from streamlit.components.v1 import html as st_html

from akko.settings import get_settings


def _copy_to_clipboard_client(text: str) -> None:
    """Copy to the browser clipboard using client-side JavaScript.

    This uses a tiny HTML/JS snippet rendered via Streamlit components to
    execute ``navigator.clipboard.writeText`` in the user's browser.
    """
    # Using a minimal, height=0 component so it doesn't affect layout.
    # The script runs on render and copies the provided text.
    safe_text = text.replace("\\", "\\\\").replace("`", "\\`")
    st_html(
        f"""
        <script>
        const t = `{safe_text}`;
        if (navigator.clipboard && navigator.clipboard.writeText) {{
            navigator.clipboard.writeText(t).catch(() => {{}});
        }} else {{
            // Fallback: create a temporary textarea
            const ta = document.createElement('textarea');
            ta.value = t;
            document.body.appendChild(ta);
            ta.select();
            try {{ document.execCommand('copy'); }} catch (e) {{ /* ignore */ }}
            document.body.removeChild(ta);
        }}
        </script>
        """,
        height=0,
    )


def try_copy(text: str, label: str = "Texte") -> None:
    """Try to copy text to clipboard with error handling.

    Behavior:
    - Attempt server-side copy with pyperclip (keeps backward compat + tests)
    - Always attempt a client-side copy in the user's browser via JS
    - Show a success toast if at least one path is attempted (assumed ok)
    - If both mechanisms fail to even render, show a warning

    Args:
        text (str): Value copied to the clipboard.
        label (str): Human-friendly label displayed in notifications.

    """
    server_copy_error: Exception | None = None
    try:
        # Best effort: this may fail on Linux servers without xclip/xsel
        pyperclip.copy(text)
    except Exception as e:  # pragma: no cover - path exercised in fallback test
        server_copy_error = e

    # Always try to copy on the client for correct browser behavior
    try:
        _copy_to_clipboard_client(text)
    except Exception:
        # Only warn if server copy also failed; otherwise we already copied
        if server_copy_error is not None:
            st.warning(f"Impossible de copier : {server_copy_error}")
        else:
            st.toast(f"{label} copié dans le presse-papiers.")
    else:
        st.toast(f"{label} copié dans le presse-papiers.")


def find_icon(category: str) -> Path | None:
    """Find an icon file for the given category.

    Args:
        category (str): Category name associated with an icon file.

    Returns:
        Path | None: Path to the matching icon, or ``None`` when not found.

    """
    SETTINGS = get_settings()
    cat_clean = category.strip().lower().replace(" ", "_").replace("-", "_")
    if not SETTINGS.icons_directory.exists():
        return None
    for icon_path in SETTINGS.icons_directory.iterdir():
        icon_name = icon_path.name.lower()
        if icon_name.startswith(cat_clean) and icon_path.suffix.lower() == ".png":
            return icon_path
    return None
