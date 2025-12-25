#!/usr/bin/env python
"""
Launcher script for tigertag GUI application.
This script handles path setup and launches the GUI.
"""
import sys
import os
from pathlib import Path

# Get the directory where this script/executable is located
if getattr(sys, 'frozen', False):
    # Running as compiled executable (PyInstaller)
    # When frozen, metadata files are extracted to sys._MEIPASS
    BASE_DIR = Path(sys.executable).parent
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    if hasattr(sys, '_MEIPASS'):
        MEIPASS = Path(sys._MEIPASS)
        # Metadata files should be in MEIPASS/metadata/parquet_files
        METADATA_DIR = MEIPASS / "metadata"
    else:
        METADATA_DIR = BASE_DIR / "metadata"
else:
    # Running as script
    BASE_DIR = Path(__file__).parent
    METADATA_DIR = BASE_DIR / "metadata"

# Add the src directory to Python path so imports work
SRC_DIR = BASE_DIR / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

# Change to tigertag directory for relative imports
TIGERTAG_DIR = SRC_DIR / "tigertag"
if TIGERTAG_DIR.exists():
    os.chdir(str(TIGERTAG_DIR))
    sys.path.insert(0, str(TIGERTAG_DIR))

# Now import and run the GUI
if __name__ == "__main__":
    try:
        import tkinter as tk
        import metadata_handler
        from gui import ToolGUI
        
        # Patch metadata_handler to use correct path when frozen
        if getattr(sys, 'frozen', False):
            def patched_load_parquet_folder():
                """Load parquet files from the bundled location."""
                if hasattr(sys, '_MEIPASS'):
                    metadata_path = Path(sys._MEIPASS) / "metadata" / "parquet_files"
                else:
                    metadata_path = BASE_DIR / "metadata" / "parquet_files"
                
                import pandas as pd
                datasets = {}
                for parquet_file in metadata_path.glob('*.parquet'):
                    key = parquet_file.stem
                    datasets[key] = pd.read_parquet(parquet_file)
                return datasets
            
            metadata_handler.load_parquet_folder = patched_load_parquet_folder
        
        from metadata_handler import load_parquet_folder
        
        # Create root window
        root = tk.Tk()
        
        # Load metadata
        metadata_dict = load_parquet_folder()
        artists = metadata_dict.keys()
        
        # Create and run GUI
        app = ToolGUI(root, artists=artists, metadata_dict=metadata_dict)
        root.mainloop()
        
    except Exception as e:
        # Show error message if something goes wrong
        import tkinter.messagebox as messagebox
        import traceback
        
        error_msg = f"Error starting application:\n\n{str(e)}\n\n{traceback.format_exc()}"
        messagebox.showerror("Error", error_msg)
        sys.exit(1)

