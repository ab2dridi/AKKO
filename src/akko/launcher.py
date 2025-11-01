"""
Launcher module for AKKO application.
"""

import os
import subprocess
import sys

from akko.helpers import find_package_path

def launch():
    """Launch the AKKO Streamlit application."""
    try:
        package_path = find_package_path()
        app_path = package_path / "front" / "app.py"
        app_dir = app_path.parent

        # Change to the app directory
        os.chdir(str(app_dir))

        # Launch Streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error launching AKKO: {e}")
        sys.exit(1)


if __name__ == "__main__":
    launch()
