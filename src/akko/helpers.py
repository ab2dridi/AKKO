import os

import pyperclip
import streamlit as st
from pathlib import Path

import akko
from akko.security import ICON_DIR

def find_package_path() -> Path:
    """Find the path to the installed AKKO package.

    Returns:
        pathlib.Path: The path to the installed AKKO package directory.
    """
    init_path = Path(akko.__file__)

    package_path = init_path.parent

    return package_path

def try_copy(text: str, label="Texte"):
    try:
        pyperclip.copy(text)
        st.toast(f"{label} copié dans le presse-papiers.")
    except Exception as e:
        st.warning(f"Impossible de copier : {e}")


def find_icon(category: str):
    cat_clean = category.strip().lower().replace(" ", "_").replace("-", "_")
    for f in os.listdir(ICON_DIR):
        if f.lower().startswith(cat_clean) and f.lower().endswith(".png"):
            return os.path.join(ICON_DIR, f)
    return None
