import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

def load_config():
    """Load the AKKO configuration file."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("config.json not found. Please add it to the root directory.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing config.json: {e}")
