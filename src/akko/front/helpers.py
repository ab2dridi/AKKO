import secrets
from pathlib import Path

import orjson
from streamlit.components.v1 import html as st_html

from akko.settings import get_settings


def copy_button(text: str, label: str = "Copier") -> None:
    """Copy to the browser clipboard using client-side JavaScript.

    This uses a tiny HTML/JS snippet rendered via Streamlit components to
    execute ``navigator.clipboard.writeText`` in the user's browser.
    """
    unique_id = secrets.token_hex(32)
    safe_text_js = orjson.dumps(text).decode(encoding="utf-8")

    st_html(
        f"""
        <div class="stButton">
            <button id="copy-{unique_id}" type="button">
                    {label}
            </button>
        </div>
        <script>
        (function() {{
          const btn = document.getElementById('copy-{unique_id}');
          const txt = {safe_text_js};
          if (!btn) return;

          btn.addEventListener('click', async () => {{
            try {{
              if (navigator.clipboard && navigator.clipboard.writeText) {{
                await navigator.clipboard.writeText(txt);
              }} else {{
                // Fallback pour vieux navigateurs
                const ta = document.createElement('textarea');
                ta.value = txt;
                ta.style.position = 'fixed';
                ta.style.left = '-9999px';
                document.body.appendChild(ta);
                ta.focus();
                ta.select();
                try {{ document.execCommand('copy'); }} catch (e) {{}}
                document.body.removeChild(ta);
              }}
              const old = btn.textContent;
              btn.textContent = "Copié ✓";
              setTimeout(() => btn.textContent = old, 1200);
            }} catch (e) {{
              const old = btn.textContent;
              btn.textContent = "Échec ❌";
              setTimeout(() => btn.textContent = old, 1500);
            }}
          }});
        }})();
        </script>
        """,
        height=60,
    )


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
