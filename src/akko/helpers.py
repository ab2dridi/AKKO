import os

import pyperclip
import streamlit as st

from akko.security import ICON_DIR


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
