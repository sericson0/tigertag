from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from pathlib import Path
from typing import Dict, Union
import pandas as pd
from rapidfuzz import fuzz, process  # type: ignore
from mutagen import File as MutagenFile
from dataclasses import dataclass
import os
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TDRC, TXXX  # noqa: E401
from mutagen.id3 import TCOM, TPUB, TIT1, COMM, TENC, TPE3, TPE4
from mutagen.flac import FLAC              
from mutagen.mp4 import MP4, MP4FreeForm   
from mutagen.aiff import AIFF
from mutagen.easyid3 import EasyID3
EasyID3.RegisterTextKey("grouping", "TIT1")
EasyID3.RegisterTextKey("remixer", "TPE3")
# EasyID3.RegisterTextKey("mixartist", "TPE4")

import re
from helper_functions import strip_accents, update_filename, parse_date
from pathlib import Path

EASYID3_CANONICAL = set(EasyID3.valid_keys.keys())

@dataclass
class MetaData:
    title     : str
    orchestra : str
    genre     : str
    year      : str
    label     : str = ""
    date      : str = ""
    master    : str = ""
    composer  : str = ""
    grouping  : str = ""
    author    : str = ""
    singer    : str = ""
    pianist   : str = ""
    bassist   : str = ""
    bandoneons: str = ""
    strings   : str = ""
    comment   : str = None
    artist    : str = None
    def __post_init__(self):
        self.artist = f"{self.orchestra} - {self.singer}"
        comment = ""
        for val in ["orchestra", "singer", "date", "label", "grouping", "master", "composer", "author", "pianist",
                  "bassist", "bandoneons", "strings"]:
            if getattr(self, val) != "":
                comment += f"{val.capitalize()}: {getattr(self, val)}\n"
        self.comment = comment

def get_updated_metadata(dct: dict):
    dct = {k.lower(): v for k, v in dct.items()}
    new_metadata = MetaData(
        title      = dct.get("title", ""),
        orchestra  = dct.get("orchestra", ""),
        genre      = dct.get("genre",""),
        year       = dct.get("year", ""),
        date       = dct.get("date", ""),
        label      = dct.get("label", ""),
        grouping   = dct.get("grouping", ""),
        master     = dct.get("master", ""),
        composer   = dct.get("composer", ""),
        author     = dct.get("author", ""),
        singer     = dct.get("singer", ""),
        pianist    = dct.get("pianist", ""),
        bassist    = dct.get("bassist", ""),
        bandoneons = dct.get("bandoneons", ""),
        strings    = dct.get("strings", ""),
    )
    return new_metadata

def get_audio_metadata(path: Union[str, Path]) -> Dict[str, str]:
    """Extract a subset of metadata common across formats using *mutagen*."""
    
    # Convert to Path object if it's a string
    path = Path(path) if isinstance(path, str) else path
    
    # Check if it's an AIFF file
    if path.suffix.lower() in ['.aif', '.aiff', '.aifc']:
        try:
            audio = AIFF(path)
            if audio.tags is None:
                return {
                    "title": "",
                    "artist": "",
                    "album": "",
                    "tracknumber": "",
                    "genre": "",
                    "date": "",
                }
            
            # AIFF uses ID3 tags
            def get_id3_text(frame_id: str) -> str:
                frame = audio.tags.get(frame_id)
                return str(frame) if frame else ""
            
            # Extract track number (format: "1/12" or "1")
            track = get_id3_text("TRCK")
            track_num = track.split('/')[0] if track else ""
            
            return {
                "title": get_id3_text("TIT2"),
                "artist": get_id3_text("TPE1"),
                "album": get_id3_text("TALB"),
                "tracknumber": track_num,
                "genre": get_id3_text("TCON"),
                "date": get_id3_text("TDRC"),
            }
        except Exception:
            raise ValueError(f"Error reading AIFF file: {path}")
    
    # Handle other formats with easy=True
    audio = MutagenFile(path, easy=True)
    if audio is None:
        raise ValueError(f"Unsupported or unreadable file: {path}")
    
    def first(key: str) -> str:
        val = audio.tags.get(key) if audio.tags else None
        return val[0] if val else ""
    
    return {
        "title": first("title"),
        "artist": first("artist"),
        "album": first("album"),
        "tracknumber": first("tracknumber"),
        "genre": first("genre"),
        "label": first("label"),
        "date": first("date"),
    }


def set_mp4_freeform(tag: MP4, desc: str, value: str) -> None:
    """Write a UTF-8 FreeForm atom ----:com.apple.iTunes:<desc> = value."""
    key = f"----:com.apple.iTunes:{desc}"
    tag[key] = [MP4FreeForm(value.encode("utf-8"), dataformat=1)]


def find_candidate_rows(
        title: str, 
        catalogue: pd.DataFrame, 
        limit: int = 10, 
        threshold: int = 60) -> List[int]:
    """Return indices of the *limit* best candidate rows ranked by fuzzy token sort ratio."""
    query = strip_accents(title)
    choices = catalogue["_norm_title"].tolist()

    scored = process.extract(query, choices, scorer=fuzz.token_sort_ratio, limit=limit)
    # scored is a list of tuples (matched string, score, original index)
    return [idx for _, score, idx in scored if score >= threshold]  # adjustable threshold


def preview_diff(old: Dict[str, str], new: Dict[str, str]) -> None:
    """Pretty‑print the tag changes before applying them."""
    print("\nProposed tag updates (empty = unchanged):")
    print(" ──────────────────────────────────────────────────────────")
    for key in sorted(set(old) | set(new)):
        old_val, new_val = old.get(key, ""), new.get(key, "")
        mark = "✓" if old_val != new_val else " "
        print(f" {mark} {key.capitalize():12} : '{old_val}' → '{new_val}'")
    print(" ──────────────────────────────────────────────────────────\n")

# def save_mp3_metadata(path: Path, new_meta: MetaData) -> None:
#     audio = EasyID3(path)
#     audio["title"] = new_meta.title
#     audio["artist"] = new_meta.artist
#     audio["genre"] = new_meta.genre
#     audio["date"] = new_meta.year
#     audio["grouping"] = [new_meta.grouping]
#     audio["composer"] = [new_meta.composer]
#     audio["comment"] = new_meta.comment
#     audio["remixer"] = [audio.get("publisher", [""])[0]]          # Now works!
#     # audio["MixArtist"] = 
#     # Clear label and set new publisher
#     audio["publisher"] = new_meta.label
#     audio.save(v2_version=3)   # ID3v2.3 for maximum compatibility


def save_mp3_metadata(path: Path, new_meta: MetaData) -> None:
    """Write metadata to MP3 using regular ID3 (all fields supported)."""
    try:
        audio = ID3(path)
    except:
        # If no ID3 tag exists, create one
        audio = ID3()
    
    # Standard fields
    audio.add(TIT2(encoding=3, text=new_meta.title))        # Title
    audio.add(TPE1(encoding=3, text=new_meta.artist))       # Artist
    audio.add(TCON(encoding=3, text=new_meta.genre))        # Genre
    audio.add(TDRC(encoding=3, text=new_meta.year))         # Date/Year
    audio.add(TCOM(encoding=3, text=new_meta.composer))     # Composer
    # Get existing label/publisher
    old_label = ""
    if 'TPUB' in audio:
        old_label = str(audio['TPUB'].text[0])
    # Move old label to remixer field (TPE3)
    if old_label:
        audio.add(TPE4(encoding=3, text=old_label))
    # audio.add(TPE3(encoding=3, text=audionew_meta.label))         # Remixer
    audio.add(TIT1(encoding=3, text=new_meta.grouping))     # Grouping/Content Group
    audio.add(TPUB(encoding=3, text=new_meta.label))
    # Comment (requires special structure)
    audio.add(COMM(encoding=3, lang='eng', desc='', text=new_meta.comment))
    
    audio.save(path, v2_version=3)

def save_m4a_metadata(path: Path, new_meta: MetaData) -> None:
    audio = MP4(path)
    audio["©nam"] = [new_meta.title]
    audio["©ART"] = [new_meta.artist]
    audio["©gen"] = [new_meta.genre]
    audio["©grp"] = [new_meta.grouping]
    audio["©day"] = [new_meta.year]
    audio["©cmt"] = new_meta.comment
    audio["©wrt"] = [new_meta.composer]
    # audio["©pub"] = [new_meta.label]
    set_mp4_freeform(audio, "REMIXER", new_meta.pianist)
    # set_mp4_freeform(audio, "Label", new_meta.label)
    audio.save()

def save_aiff_metadata(path: Path, new_meta) -> None:
    """Update AIFF metadata based on existing structure."""
    audio = AIFF(path)
    
    if audio.tags is None:
        audio.add_tags()
    
    # Direct dictionary-style assignment
    audio.tags['TIT2'] = TIT2(encoding=3, text=new_meta.title)
    audio.tags['TPE1'] = TPE1(encoding=3, text=new_meta.artist)
    audio.tags['TCON'] = TCON(encoding=3, text=new_meta.genre)
    audio.tags['TDRC'] = TDRC(encoding=3, text=new_meta.year)
    audio.tags['TCOM'] = TCOM(encoding=3, text=new_meta.composer)
    audio.tags['TPUB'] = TPUB(encoding=3, text=new_meta.label)
    audio.tags['TIT1'] = TIT1(encoding=3, text=new_meta.grouping)
    
    # Comment with proper structure
    audio.tags['COMM::eng'] = COMM(
        encoding=3,
        lang='eng',
        desc='',
        text=new_meta.comment
    )
    
    audio.save()


def save_flac_metadata(path: Path, new_meta: MetaData) -> None:
    """Write metadata to non-MP3 files using mutagen's File interface."""
    audio = MutagenFile(path, easy=True)
    if audio is None:
        raise ValueError(f"Unsupported file for writing metadata: {path}")
    
    # Save original label/publisher to remixer BEFORE overwriting
    original_label = audio.get("label", [""])[0] if audio.get("label") else ""
    original_publisher = audio.get("publisher", [""])[0] if audio.get("publisher") else ""
    remixer_value = original_label or original_publisher  # Use label first, fallback to publisher
    audio["title"] = new_meta.title
    audio["artist"] = new_meta.artist
    audio["genre"] = new_meta.genre
    audio["date"] = new_meta.year
    audio["comment"] = new_meta.comment
    audio["composer"] = [new_meta.composer]
    audio["grouping"] = new_meta.grouping
    # Set remixer to original label/publisher value
    if remixer_value:
        audio["remixer"] = remixer_value
    
    # Clear label and set new publisher
    if "label" in audio:
        del audio["label"]  # Remove label field
    audio["publisher"] = new_meta.label

    new_meta.label
    # audio["Publisher"] = new_meta.label
    audio.save()


def write_metadata(path: Path, new_meta: Dict[str, str]) -> None:
    # open without "easy=True" so we can reach low-level tag objects
    if path.suffix.lower() == ".mp3":
        save_mp3_metadata(path, new_meta)
    elif path.suffix.lower() in {".m4a", ".mp4"}:
        save_m4a_metadata(path, new_meta)
    elif path.suffix.lower() == ".flac":
        save_flac_metadata(path, new_meta)
    elif path.suffix.lower() in (".aif", ".aiff"):
        save_aiff_metadata(path, new_meta)
    else:
        print("File Type Unsupported")

# ───────────────────────────────────────────────────────────────────────────────
# CLI flow
# ───────────────────────────────────────────────────────────────────────────────

def ask_choice(file:str, audio_metadata: dict, catalogue: pd.DataFrame) -> int | None:
    """Interactively ask the user to pick a row; return DataFrame index or None."""
    
    candidate_indices = find_candidate_rows(audio_metadata["title"], catalogue)
    if not candidate_indices:
        input_title = input(f"No match for {audio_metadata["title"]}, type title here: ")
        candidate_indices = find_candidate_rows(input_title, catalogue, threshold=30)
    if not candidate_indices:
        print(f"No candidates found for {input_title}. Skipping...")
        return 9999

    print(f"\nPossible matches for {file} - Album: {audio_metadata["album"]},Date: {audio_metadata["date"]}\n")
    if len(candidate_indices) == 1:
        print("\nOnly one candidate found, using it automatically.")
        return candidate_indices[0]
    
    for n, idx in enumerate(candidate_indices, 1):
        row = catalogue.loc[idx]
        print(f" [{n}] {row['Title']} — {row.get('Artist', '')}  (Date: {row.get('Date', '')})")

    while True:
        choice = input("\nPick a number (or 0 to skip): ")
        if choice.isdigit():
            i = int(choice)
            if i == 0:
                return 9999
            if 1 <= i <= len(candidate_indices):
                return candidate_indices[i - 1]
        print("Invalid choice. Try again.")


main_folder =  "C:/Users/seric/Music/Tango Discography/Osvaldo Pugliese" 
csv_path = main_folder + "/Discography of Osvaldo Pugliese.csv"
df = load_catalogue(csv_path)




os.listdir(main_folder)
folders = [item.name for item in Path(main_folder).iterdir() if item.is_dir()]


# print("Files in the audio folder:")
def update_tags(audio_folder, catalogue):
    for file in os.listdir(audio_folder):
        if not file.endswith(('.mp3', '.flac', '.m4a', '.mp4', "aif")):
        # if not file.endswith(('.mp3')):
            print(f"File {file} is of incompatible type. Skipping...")
            continue
        audio_file = Path(audio_folder, file)
        audio_metadata = get_audio_metadata(audio_file)

        chosen_idx = ask_choice(file, audio_metadata, catalogue)
        if chosen_idx != 9999:
            new_metadata = get_updated_metadata(catalogue.loc[chosen_idx].to_dict())
            try:
                new_path = update_filename(
                    audio_file, 
                    new_metadata.title,
                    new_metadata.orchestra,
                    new_metadata.year)
                write_metadata(new_path, new_metadata)
            except Exception as e:
                print(e)
                continue



audio_folder = Path(main_folder, folders[11])  # Use the first subfolder
print(audio_folder)
# List all files in the audio folder
start_date = 1949
end_date = 1951

update_tags(audio_folder, catalogue)
