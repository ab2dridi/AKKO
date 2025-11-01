import os
import json
import base64
import hashlib
from cryptography.fernet import Fernet
from utils.config_loader import load_config

# --- Load configuration ---
config = load_config()

# --- Data paths from config.json ---
DATA_FILE = config["data_paths"]["credentials"]
PRIVATE_LINKS_FILE = config["data_paths"]["private_links"]
PRO_LINKS_FILE = config["data_paths"]["public_links"]

# --- Derived folders ---
PRIVATE_DIR = os.path.dirname(DATA_FILE)
PUBLIC_DIR = os.path.dirname(PRO_LINKS_FILE)
ICON_DIR = os.path.join(PUBLIC_DIR, "icons")

# --- Ensure directories exist ---
os.makedirs(PRIVATE_DIR, exist_ok=True)
os.makedirs(PUBLIC_DIR, exist_ok=True)
os.makedirs(ICON_DIR, exist_ok=True)


# --- Encryption helpers ---
def derive_key(master_password: str) -> bytes:
    """
    Derive a Fernet-compatible key from the given master password.
    """
    key = hashlib.sha256(master_password.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key)


# --- Credentials management ---
def load_data(fernet: Fernet) -> list:
    """
    Load and decrypt credentials data.
    - Returns [] if the file doesn't exist (new vault scenario).
    - Raises ValueError on invalid password.
    """
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "rb") as f:
        encrypted = f.read()
    try:
        decrypted = fernet.decrypt(encrypted)
    except InvalidToken as e:
        # signaler un mauvais mot de passe
        raise ValueError("Invalid master password") from e
    return json.loads(decrypted.decode("utf-8"))



def save_data(data: list, fernet: Fernet):
    """
    Encrypt and save credentials data to disk.
    """
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    encrypted = fernet.encrypt(payload)
    with open(DATA_FILE, "wb") as f:
        f.write(encrypted)


# --- Links management ---
def _init_links_file(path: str) -> dict:
    """
    Create an empty link file if it doesn't exist.
    """
    if not os.path.exists(path):
        data = {"categories": [], "links": []}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"categories": [], "links": []}


def load_links() -> dict:
    """
    Load public and private links from separate JSON files.
    """
    private_links = _init_links_file(PRIVATE_LINKS_FILE)
    pro_links = _init_links_file(PRO_LINKS_FILE)
    return {"perso": private_links, "pro": pro_links}


def save_links(links: dict):
    """
    Save public and private links into their respective JSON files.
    """
    if "perso" in links:
        with open(PRIVATE_LINKS_FILE, "w", encoding="utf-8") as f:
            json.dump(links["perso"], f, indent=2, ensure_ascii=False)

    if "pro" in links:
        with open(PRO_LINKS_FILE, "w", encoding="utf-8") as f:
            json.dump(links["pro"], f, indent=2, ensure_ascii=False)
