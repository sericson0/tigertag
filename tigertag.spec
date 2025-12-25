# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for tigertag GUI application.
This bundles the application into a single executable.
"""

import os
from pathlib import Path

block_cipher = None

# Get the project root directory (where this spec file is located)
# SPEC is a built-in PyInstaller variable pointing to this spec file
try:
    project_root = Path(os.path.dirname(os.path.abspath(SPEC)))
except NameError:
    # Fallback if SPEC is not available (shouldn't happen in PyInstaller)
    project_root = Path(__file__).parent if '__file__' in globals() else Path.cwd()

# Paths
src_dir = project_root / "src"
tigertag_dir = src_dir / "tigertag"
metadata_dir = project_root / "metadata"

# Collect all Python files in tigertag package
a = Analysis(
    ['launcher.py'],
    pathex=[
        str(project_root),
        str(src_dir),
        str(tigertag_dir),
    ],
    binaries=[],
    datas=[
        # Include metadata parquet files
        (str(metadata_dir / "parquet_files"), "metadata/parquet_files"),
    ] + (
        # Include config file if it exists
        [(str(tigertag_dir / "tigertag_config.json"), "tigertag")] 
        if (tigertag_dir / "tigertag_config.json").exists() 
        else []
    ),
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.scrolledtext',
        'pandas',
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.base',
        'pandas._libs.tslibs.conversion',
        'pyarrow',
        'pyarrow.parquet',
        'mutagen',
        'mutagen.id3',
        'mutagen.flac',
        'mutagen.mp4',
        'mutagen.aiff',
        'mutagen.easyid3',
        'pygame',
        'pygame.mixer',
        'rapidfuzz',
        'rapidfuzz.fuzz',
        'rapidfuzz.process',
        'config_handler',
        'metadata_handler',
        'helper_functions',
        'tag_updater',
        'vdj_updater',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# No need to filter - we're not using None anymore

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TigerTag',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # You can add an .ico file path here if you have one
)

