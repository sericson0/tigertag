"""Configuration handler for saving and loading application settings."""
import json
from pathlib import Path
from typing import Optional, List

CONFIG_FILE = Path(__file__).parent / "tigertag_config.json"

def load_config() -> dict:
    """Load configuration from file, return default if file doesn't exist."""
    default_config = {
        "vdj_database_path": "",
        "link_database": False,
        "folder_paths": [],
        "output_folder_path": "",
        "start_year": "1900",
        "end_year": "2050",
        "filename_format": "leader last - title - singer last - year",
        "convert_aflac_to_flac": False,
        "convert_to_mono": False,
        "convert_to_48khz": False,
        "use_24bit": False,
        "normalize_audio": False,
        "aufs_target": "-13.0",
        "output_structure": "preserve",
        "auto_select": False,
        "year_match": False,
        "artist_format": "leader - singer",
        "selected_artists": [],
        "enable_vst3": False,
        "vst3_plugins": [],
        "vst3_parameters": []
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

def get_folder_paths() -> List[str]:
    """Get the list of folder paths from config."""
    config = load_config()
    return config.get("folder_paths", [])

def set_folder_paths(paths: List[str]) -> None:
    """Set the list of folder paths in config."""
    config = load_config()
    config["folder_paths"] = paths
    save_config(config)

def get_output_folder_path() -> str:
    """Get the output folder path from config."""
    config = load_config()
    return config.get("output_folder_path", "")

def set_output_folder_path(path: str) -> None:
    """Set the output folder path in config."""
    config = load_config()
    config["output_folder_path"] = path
    save_config(config)

def get_start_year() -> str:
    """Get the start year from config."""
    config = load_config()
    return config.get("start_year", "1900")

def set_start_year(year: str) -> None:
    """Set the start year in config."""
    config = load_config()
    config["start_year"] = year
    save_config(config)

def get_end_year() -> str:
    """Get the end year from config."""
    config = load_config()
    return config.get("end_year", "2050")

def set_end_year(year: str) -> None:
    """Set the end year in config."""
    config = load_config()
    config["end_year"] = year
    save_config(config)

def get_filename_format() -> str:
    """Get the filename format from config."""
    config = load_config()
    return config.get("filename_format", "leader last - title - singer last - year")

def set_filename_format(format_str: str) -> None:
    """Set the filename format in config."""
    config = load_config()
    config["filename_format"] = format_str
    save_config(config)

def get_audio_processing_settings() -> dict:
    """Get all audio processing settings from config."""
    config = load_config()
    return {
        "convert_aflac_to_flac": config.get("convert_aflac_to_flac", False),
        "convert_to_mono": config.get("convert_to_mono", False),
        "convert_to_48khz": config.get("convert_to_48khz", False),
        "use_24bit": config.get("use_24bit", False),
        "normalize_audio": config.get("normalize_audio", False),
        "aufs_target": config.get("aufs_target", "-13.0"),
    }

def set_audio_processing_settings(settings: dict) -> None:
    """Set all audio processing settings in config."""
    config = load_config()
    config.update(settings)
    save_config(config)

def get_output_structure() -> str:
    """Get the output structure setting from config."""
    config = load_config()
    return config.get("output_structure", "preserve")

def set_output_structure(structure: str) -> None:
    """Set the output structure in config."""
    config = load_config()
    config["output_structure"] = structure
    save_config(config)

def get_auto_select() -> bool:
    """Get the auto-select setting from config."""
    config = load_config()
    return config.get("auto_select", False)

def set_auto_select(enabled: bool) -> None:
    """Set the auto-select setting in config."""
    config = load_config()
    config["auto_select"] = enabled
    save_config(config)

def get_year_match() -> bool:
    """Get the year-match setting from config."""
    config = load_config()
    return config.get("year_match", False)

def set_year_match(enabled: bool) -> None:
    """Set the year-match setting in config."""
    config = load_config()
    config["year_match"] = enabled
    save_config(config)

def get_artist_format() -> str:
    """Get the artist format setting from config."""
    config = load_config()
    return config.get("artist_format", "leader - singer")

def set_artist_format(format_str: str) -> None:
    """Set the artist format setting in config."""
    config = load_config()
    config["artist_format"] = format_str
    save_config(config)

def get_selected_artists() -> List[str]:
    """Get the list of selected artists from config."""
    config = load_config()
    return config.get("selected_artists", [])

def set_selected_artists(artists: List[str]) -> None:
    """Set the list of selected artists in config."""
    config = load_config()
    config["selected_artists"] = artists
    save_config(config)

def get_enable_vst3() -> bool:
    """Get the enable VST3 setting from config."""
    config = load_config()
    return config.get("enable_vst3", False)

def set_enable_vst3(enabled: bool) -> None:
    """Set the enable VST3 setting in config."""
    config = load_config()
    config["enable_vst3"] = enabled
    save_config(config)

def get_vst3_plugins() -> List[str]:
    """Get the list of VST3 plugin paths from config."""
    config = load_config()
    return config.get("vst3_plugins", [])

def set_vst3_plugins(plugins: List[str]) -> None:
    """Set the list of VST3 plugin paths in config."""
    config = load_config()
    config["vst3_plugins"] = plugins
    save_config(config)

def get_vst3_parameters() -> List[dict]:
    """Get the list of VST3 plugin parameters from config."""
    config = load_config()
    return config.get("vst3_parameters", [])

def set_vst3_parameters(parameters: List[dict]) -> None:
    """Set the list of VST3 plugin parameters in config."""
    config = load_config()
    config["vst3_parameters"] = parameters
    save_config(config)

def save_all_settings(settings: dict) -> None:
    """Save all settings at once."""
    config = load_config()
    config.update(settings)
    save_config(config)

