from pathlib import Path

import pyperclip
import streamlit as st

from akko.settings import get_settings


def try_copy(text: str, label: str = "Texte") -> None:
    """Try to copy text to clipboard with error handling."""
    try:
        pyperclip.copy(text)
        st.toast(f"{label} copié dans le presse-papiers.")
    except Exception as e:
        st.warning(f"Impossible de copier : {e}")


def find_icon(category: str) -> Path | None:
    """Find an icon file for the given category."""
    SETTINGS = get_settings()
    cat_clean = category.strip().lower().replace(" ", "_").replace("-", "_")
    if not SETTINGS.icons_directory.exists():
        return None
    for icon_path in SETTINGS.icons_directory.iterdir():
        icon_name = icon_path.name.lower()
        if icon_name.startswith(cat_clean) and icon_path.suffix.lower() == ".png":
            return icon_path
    return None
