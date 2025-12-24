"""Configuration handler for saving and loading application settings."""
import json
from pathlib import Path
from typing import Optional

CONFIG_FILE = Path(__file__).parent / "tigertag_config.json"

def load_config() -> dict:
    """Load configuration from file, return default if file doesn't exist."""
    default_config = {
        "vdj_database_path": "",
        "link_database": False
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                default_config.update(config)
                return default_config
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}. Using defaults.")
            return default_config
    
    return default_config

def save_config(config: dict) -> None:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving config: {e}")

def get_vdj_database_path() -> Optional[str]:
    """Get the Virtual DJ database path from config."""
    config = load_config()
    path = config.get("vdj_database_path", "")
    return path if path else None

def set_vdj_database_path(path: str) -> None:
    """Set the Virtual DJ database path in config."""
    config = load_config()
    config["vdj_database_path"] = path
    save_config(config)

def is_link_database_enabled() -> bool:
    """Check if database linking is enabled."""
    config = load_config()
    return config.get("link_database", False)

def set_link_database(enabled: bool) -> None:
    """Set database linking enabled/disabled."""
    config = load_config()
    config["link_database"] = enabled
    save_config(config)

