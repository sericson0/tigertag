# Building TigerTag Executable

This guide explains how to build a Windows executable (.exe) for the TigerTag application.

## Requirements

- Python 3.13 or higher
- All project dependencies installed (see `pyproject.toml`)
- PyInstaller (will be installed automatically by the build script)

## Quick Build

1. Open a terminal/command prompt in the project root directory.

2. Run the build script:
   ```bash
   python build_exe.py
   ```

   The script will:
   - Check for PyInstaller and install it if needed
   - Build the executable using the `tigertag.spec` configuration
   - Create `TigerTag.exe` in the `dist/` folder

3. Find your executable at: `dist/TigerTag.exe`

## Manual Build (Alternative)

If you prefer to build manually:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Run PyInstaller with the spec file:
   ```bash
   pyinstaller --clean tigertag.spec
   ```

## What's Included

The executable includes:
- Python interpreter (bundled, no separate installation needed)
- All Python dependencies (pandas, pygame, mutagen, etc.)
- All application code
- Metadata parquet files
- Configuration files

## Distribution

You can distribute `TigerTag.exe` to users. They don't need:
- Python installed
- Any dependencies installed
- Command line access

Users can simply double-click `TigerTag.exe` to run the application.

## Notes

- The executable file will be quite large (100-200MB) because it includes Python and all dependencies
- First launch may take a few seconds as PyInstaller extracts files to a temporary location
- Antivirus software may flag the executable; this is normal for PyInstaller executables

## Troubleshooting

If the build fails:
1. Ensure all dependencies are installed: `pip install -e .`
2. Check that all metadata files exist in `metadata/parquet_files/`
3. Review the build output for specific error messages
4. Try building with `console=True` in the spec file to see error messages

If the executable doesn't run:
1. Check that metadata files are included (they should be in the bundle)
2. Try running with console enabled to see error messages
3. Ensure all required files are present in the project structure

