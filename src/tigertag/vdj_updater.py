"""Virtual DJ database XML updater."""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Optional
import shutil
from datetime import datetime

def update_vdj_database(
    vdj_db_path: str,
    filename_changes: List[Tuple[str, str]],
    audio_folder: str
) -> Tuple[int, Optional[str]]:
    """
    Update Virtual DJ database XML file with new file paths.
    
    Parameters:
    -----------
    vdj_db_path : str
        Path to the Virtual DJ database.xml file
    filename_changes : List[Tuple[str, str]]
        List of (old_filename, new_filename) tuples
    audio_folder : str
        Path to the audio folder containing the files
    
    Returns:
    --------
    Tuple[int, Optional[str]]
        (number of updated entries, error message if any)
    """
    if not vdj_db_path or not Path(vdj_db_path).exists():
        return 0, f"Virtual DJ database file not found: {vdj_db_path}"
    
    if not filename_changes:
        return 0, None
    
    try:
        # Create backup before modifying
        backup_path = Path(vdj_db_path).with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xml')
        shutil.copy2(vdj_db_path, backup_path)
        
        # Parse XML
        tree = ET.parse(vdj_db_path)
        root = tree.getroot()
        
        # Convert audio folder to Path for consistent path handling
        audio_folder_path = Path(audio_folder).resolve()
        
        updated_count = 0
        
        # Create a mapping of old to new filenames (case-insensitive for Windows)
        filename_map = {}
        for old, new in filename_changes:
            # Store lowercase version for case-insensitive matching
            filename_map[old.lower()] = new
        
        # Find all Song elements and update FilePath attributes
        for song in root.findall('.//Song'):
            filepath_attr = song.get('FilePath')
            if not filepath_attr:
                continue
            
            # Convert to Path for comparison
            try:
                filepath = Path(filepath_attr)
            except:
                continue
            
            # Get the filename from the filepath
            old_filename = filepath.name
            old_filename_lower = old_filename.lower()
            
            # Check if this filename matches any of our renamed files (case-insensitive)
            if old_filename_lower in filename_map:
                new_filename = filename_map[old_filename_lower]
                
                # Update the filepath - preserve the directory structure
                new_filepath = filepath.parent / new_filename
                
                # Convert to string format (use forward slashes for XML compatibility)
                new_filepath_str = str(new_filepath).replace('\\', '/')
                
                # Update the FilePath attribute
                song.set('FilePath', new_filepath_str)
                updated_count += 1
        
        # Save the updated XML
        tree.write(vdj_db_path, encoding='utf-8', xml_declaration=True)
        
        return updated_count, None
        
    except ET.ParseError as e:
        return 0, f"Error parsing XML: {str(e)}"
    except Exception as e:
        return 0, f"Error updating Virtual DJ database: {str(e)}"

