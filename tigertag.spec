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

# Try to collect rapidfuzz binaries using collect_all if available
try:
    from PyInstaller.utils.hooks import collect_all, collect_submodules
    rapidfuzz_datas, rapidfuzz_binaries, rapidfuzz_hiddenimports = collect_all('rapidfuzz')
    # Collect all rapidfuzz submodules
    rapidfuzz_hiddenimports.extend(collect_submodules('rapidfuzz'))
except ImportError:
    # Fallback if PyInstaller hooks not available during spec execution
    rapidfuzz_datas = []
    rapidfuzz_binaries = []
    rapidfuzz_hiddenimports = []

# Collect all Python files in tigertag package
a = Analysis(
    ['launcher.py'],
    pathex=[
        str(project_root),
        str(src_dir),
        str(tigertag_dir),
    ],
    binaries=rapidfuzz_binaries,
    datas=[
        # Include metadata parquet files
        (str(metadata_dir / "parquet_files"), "metadata/parquet_files"),
    ] + rapidfuzz_datas + (
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
        'rapidfuzz.distance',
        'rapidfuzz.distance.Levenshtein',
        'rapidfuzz.distance._initialize',
        'rapidfuzz.fuzz_py',
        'rapidfuzz.process_py',
        'rapidfuzz._utils',
        'rapidfuzz._common',
        'rapidfuzz_capi',
        'rapidfuzz_cpp',
        'rapidfuzz.str_utils',
        'config_handler',
        'metadata_handler',
        'helper_functions',
        'tag_updater',
        'vdj_updater',
    ] + rapidfuzz_hiddenimports,
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
    icon=str(project_root / "docs" / "logo.ico") if (project_root / "docs" / "logo.ico").exists() else (
        str(project_root / "docs" / "logo.png") if (project_root / "docs" / "logo.png").exists() else None
    ),  # Prefer .ico for Windows, PNG may work but .ico is recommended
)

