import unicodedata
from pathlib import Path
import re
import pandas as pd
from datetime import datetime
def strip_accents(text: str) -> str:
    """Return *text* lower‑cased and stripped of diacritics (accents)."""
    nfkd_form = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()


def update_filename(path: Path, title: str, orchestra: str = "", year: str = "", 
                   format_type: str = "orchestra - title - year", 
                   artist_last_name: str = "", orchestra_last_name: str = "") -> Path:
    """Rename the file to a slugified version based on the selected format, preserving the extension."""
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    # Build tag title based on format
    if format_type == "orchestra - title - year":
        if orchestra != "" and year != "":
            tag_title = f"{orchestra} - {title} - {year}"
        elif orchestra != "":
            tag_title = f"{orchestra} - {title}"
        else:
            tag_title = title
    elif format_type == "orchestra last - singer last - title - year":
        # Use artist_last_name which already contains "orchestra_last_name - singer_last_name"
        if artist_last_name != "" and year != "":
            tag_title = f"{artist_last_name} - {title} - {year}"
        elif artist_last_name != "":
            tag_title = f"{artist_last_name} - {title}"
        else:
            tag_title = title
    elif format_type == "orchestra last - title - year":
        if orchestra_last_name != "" and year != "":
            tag_title = f"{orchestra_last_name} - {title} - {year}"
        elif orchestra_last_name != "":
            tag_title = f"{orchestra_last_name} - {title}"
        else:
            tag_title = title
    else:
        # Default to original behavior
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
        print("_"*80,"\n","_"*80, "\n"*5)
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
    
    # Check for "00" in month or day positions for common formats
    # Handle dates like "00/15/2024", "01/00/2024", "00/00/2024"
    has_zero_month = False
    has_zero_day = False
    
    # Try to detect and handle "00" values before parsing
    # Common formats: M/D/YYYY, D/M/YYYY, YYYY-M-D, etc.
    zero_patterns = [
        (r'^00[/-](\d{1,2})[/-](\d{4})$', 'month'),  # 00/15/2024 or 00-15-2024
        (r'^(\d{1,2})[/-]00[/-](\d{4})$', 'day'),     # 15/00/2024 or 15-00-2024
        (r'^00[/-]00[/-](\d{4})$', 'both'),           # 00/00/2024 or 00-00-2024
        (r'^(\d{4})[/-]00[/-](\d{1,2})$', 'month'),   # 2024-00-15
        (r'^(\d{4})[/-](\d{1,2})[/-]00$', 'day'),     # 2024-15-00
        (r'^(\d{4})[/-]00[/-]00$', 'both'),           # 2024-00-00
    ]
    
    year = None
    month = None
    day = None
    
    for pattern, zero_type in zero_patterns:
        match = re.match(pattern, date_str)
        if match:
            if zero_type == 'month':
                # Format: 00/D/YYYY or YYYY-00-D
                if len(match.groups()) == 2:
                    if date_str.startswith('00'):
                        # 00/D/YYYY format
                        day = int(match.group(1))
                        year = int(match.group(2))
                        month = 0
                    else:
                        # YYYY-00-D format
                        year = int(match.group(1))
                        day = int(match.group(2))
                        month = 0
            elif zero_type == 'day':
                # Format: M/00/YYYY or YYYY-M-00
                if len(match.groups()) == 2:
                    if '/' in date_str or '-' in date_str:
                        parts = re.split(r'[/-]', date_str)
                        if len(parts) == 3:
                            if parts[1] == '00':
                                # M/00/YYYY format
                                month = int(parts[0])
                                year = int(parts[2])
                                day = 0
                            elif parts[2] == '00':
                                # YYYY-M-00 format
                                year = int(parts[0])
                                month = int(parts[1])
                                day = 0
            elif zero_type == 'both':
                # Format: 00/00/YYYY or YYYY-00-00
                if len(match.groups()) == 1:
                    year = int(match.group(1))
                    month = 0
                    day = 0
            
            if year is not None:
                # Construct output string with "00" preserved
                return f"{year:04d}-{month:02d}-{day:02d}" if month == 0 or day == 0 else f"{year:04d}-{month:02d}-{day:02d}"
    
    # If no "00" pattern matched, try normal parsing with temporary "01" replacement
    # This handles edge cases where "00" might appear in other positions
    temp_date_str = date_str
    if '00' in date_str:
        # Replace "00" with "01" temporarily for parsing
        temp_date_str = date_str.replace('/00/', '/01/').replace('-00-', '-01-')
        temp_date_str = re.sub(r'^00/', '01/', temp_date_str)
        temp_date_str = re.sub(r'/00/', '/01/', temp_date_str)
        temp_date_str = re.sub(r'^00-', '01-', temp_date_str)
        temp_date_str = re.sub(r'-00-', '-01-', temp_date_str)
        temp_date_str = re.sub(r'-00$', '-01', temp_date_str)
        temp_date_str = re.sub(r'/00$', '/01', temp_date_str)
    
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
    
    # Try each format with the potentially modified date string
    for fmt in formats:
        try:
            parsed = datetime.strptime(temp_date_str, fmt)
            result_year = parsed.year
            result_month = parsed.month
            result_day = parsed.day
            
            # Check if we replaced "00" values and restore them
            if '00' in date_str:
                # Determine which component was "00" by comparing original and temp
                original_parts = re.split(r'[/-]', date_str)
                temp_parts = re.split(r'[/-]', temp_date_str)
                
                # For M/D/YYYY format
                if fmt in ['%m/%d/%Y', '%m-%d-%Y']:
                    if original_parts[0] == '00':
                        result_month = 0
                    if len(original_parts) > 1 and original_parts[1] == '00':
                        result_day = 0
                # For D/M/Y format
                elif fmt in ['%d/%m/%Y', '%d-%m-%Y']:
                    if original_parts[0] == '00':
                        result_day = 0
                    if len(original_parts) > 1 and original_parts[1] == '00':
                        result_month = 0
                # For Y/M/D format
                elif fmt in ['%Y/%m/%d', '%Y-%m-%d']:
                    if len(original_parts) > 1 and original_parts[1] == '00':
                        result_month = 0
                    if len(original_parts) > 2 and original_parts[2] == '00':
                        result_day = 0
            
            return f"{result_year:04d}-{result_month:02d}-{result_day:02d}"
        except ValueError:
            continue
    
    # If none work, try pandas to_datetime as fallback (very flexible)
    try:
        parsed = pd.to_datetime(temp_date_str, errors='raise')
        if pd.notna(parsed):
            result_year = parsed.year
            result_month = parsed.month
            result_day = parsed.day
            
            # Restore "00" values if they existed
            if '00' in date_str:
                original_parts = re.split(r'[/-]', date_str)
                if len(original_parts) >= 2:
                    # Try to infer format from original string
                    if date_str.count('/') == 2:
                        parts = date_str.split('/')
                        if parts[0] == '00':
                            result_month = 0
                        elif len(parts) > 1 and parts[1] == '00':
                            result_day = 0
            
            return f"{result_year:04d}-{result_month:02d}-{result_day:02d}"
    except:
        pass
    
    # If still fails, return None (will show which ones failed)
    print(f"Warning: Could not parse date: '{date_str}'")
    return None


def subset_entries(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return df[df["Year"].astype(int).between(start_year, end_year)].reset_index(drop=True)


def parse_years_from_folder(folder_path):
    """
    Parse year information from folder name.
    
    Parameters:
    -----------
    folder_path : str or Path
        Full path or just folder name
    
    Returns:
    --------
    tuple : (start_year, end_year) or (None, None) if no years found
    
    Examples:
    ---------
    "Victor 1935-1940" -> (1935, 1940)
    "Odeon 1938-41" -> (1938, 1941)
    "Biagi 1927" -> (1927, 1927)
    "Gotan" -> (None, None)
    """
    # Get just the folder name (not full path)
    folder_name = Path(folder_path).name
    
    # Pattern to match years (4 digits or 2 digits)
    # Looks for: YYYY-YYYY, YYYY-YY, or just YYYY
    pattern = r'(\d{4})(?:\s*[-–]\s*(\d{2,4}))?'
    
    matches = re.findall(pattern, folder_name)
    
    if not matches:
        return None, None
    
    # Get the last match (in case there are multiple year patterns)
    match = matches[-1]
    start_year_str = match[0]
    end_year_str = match[1] if match[1] else None
    
    start_year = int(start_year_str)
    
    if end_year_str:
        end_year = int(end_year_str)
        
        # If end year is 2 digits, infer the century from start year
        if end_year < 100:
            # Get the century from start year
            century = (start_year // 100) * 100
            end_year = century + end_year
            
            # Handle case where end year wraps to next century
            # e.g., 1998-02 should be 1998-2002, not 1998-1902
            if end_year < start_year:
                end_year += 100
    else:
        # Only one year found, use it for both start and end
        end_year = start_year
    
    return start_year, end_year
