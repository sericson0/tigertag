import unicodedata
from pathlib import Path
import re
def strip_accents(text: str) -> str:
    """Return *text* lower‑cased and stripped of diacritics (accents)."""
    nfkd_form = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()


def update_filename(path: Path, title: str) -> None:
    """Rename the file to a slugified version of the title, preserving the extension."""
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    safe_title = slugify_filename(title)

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

