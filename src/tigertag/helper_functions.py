import unicodedata
from pathlib import Path
import re
import pandas as pd
from datetime import datetime
def strip_accents(text: str) -> str:
    """Return *text* lower‑cased and stripped of diacritics (accents)."""
    nfkd_form = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()


def update_filename(path: Path, title: str, orchestra: str = "", year: str = "") -> Path:
    """Rename the file to a slugified version of the title, preserving the extension."""
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    tag_title = title
    if orchestra != "" and year != "":
        tag_title = f"{orchestra} - {title} - {year}"
    elif orchestra != "":
        tag_title = f"{orchestra} - {title}"

    safe_title = slugify_filename(tag_title)

    new_path = path.with_name(f"{safe_title}{path.suffix.lower()}")
    # No rename if filename is already correct (case-insensitive on Windows)
    if new_path.resolve() != path.resolve():
        counter = 1
        while new_path.exists():
            new_path = path.with_name(f"{safe_title} ({counter}){path.suffix.lower()}")
            counter += 1

        path.rename(new_path)
        print(f"Renamed `{path.stem}` →→→ `{new_path.name}`")
    else:
        print(f"Kept name `{new_path.name}`")
    return new_path




def slugify_filename(text: str, fallback: str = "untitled") -> str:
    """
    Return *text* stripped of accents, illegal characters and leading/trailing
    whitespace so it is safe as a filename on all major OSes.
    """
    if not text:
        text = fallback

    # Strip accents → “Canción” → “Cancion”
    text = unicodedata.normalize("NFKD", text)
    text = "".join([c for c in text if not unicodedata.combining(c)])

    # Replace path separators and other illegal chars with underscores
    text = re.sub(r'[\/\\\?\%\*\:\|"<>\.]', "_", text)

    # Collapse consecutive underscores/spaces and trim
    text = re.sub(r"[_\s]+", " ", text).strip()

    # Very long titles make unwieldy filenames
    return text[:120] if len(text) > 120 else text



def parse_date(date_str):
    if not date_str or pd.isna(date_str) or str(date_str).strip() == "":
        return None
    
    # Clean the input
    date_str = str(date_str).strip()
    
    # List of common date formats to try
    formats = [
        '%Y-%m-%d',      # 2024-01-15
        '%m/%d/%Y',      # 01/15/2024
        '%d/%m/%Y',      # 15/01/2024
        '%Y/%m/%d',      # 2024/01/15
        '%m-%d-%Y',      # 01-15-2024
        '%d-%m-%Y',      # 15-01-2024
        '%b %d, %Y',     # Jan 15, 2024
        '%B %d, %Y',     # January 15, 2024
        '%d %b %Y',      # 15 Jan 2024
        '%d %B %Y',      # 15 January 2024
        '%Y%m%d',        # 20240115
        '%m/%d/%y',      # 01/15/24
        '%d/%m/%y',      # 15/01/24
        '%Y.%m.%d',      # 2024.01.15
        '%d.%m.%Y',      # 15.01.2024
    ]
    
    # Try each format
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # If none work, try pandas to_datetime as fallback (very flexible)
    try:
        parsed = pd.to_datetime(date_str, errors='raise')
        if pd.notna(parsed):
            return parsed.strftime('%Y-%m-%d')
    except:
        pass
    
    # If still fails, return None (will show which ones failed)
    print(f"Warning: Could not parse date: '{date_str}'")
    return None


def subset_entries(df: pd.DataFrame, start_year: int, end_year) -> pd.DataFrame:
    return df[df["Year"].astype(int).between(start_year, end_year)].reset_index(drop=True)

