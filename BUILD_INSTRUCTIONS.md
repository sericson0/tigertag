# Building TigerTag Windows Executable

This document explains how to create a Windows `.exe` file for the TigerTag GUI application.

## Overview

The build process creates a **standalone executable** that includes:
- Python interpreter (no Python installation needed on target machines)
- All required dependencies
- All application code
- Metadata files

Users can simply double-click `TigerTag.exe` to run the application - no command line needed!

## Quick Start

1. **Install project dependencies** (if not already done):
   ```bash
   pip install -e .
   ```

2. **Run the build script**:
   ```bash
   python build_exe.py
   ```

3. **Find your executable**:
   The executable will be created at: `dist/TigerTag.exe`

That's it! You can now distribute `TigerTag.exe` to users.

## How It Works

### Build Process

1. The `build_exe.py` script checks for PyInstaller and installs it if needed
2. PyInstaller uses the `tigertag.spec` configuration file to:
   - Bundle Python and all dependencies
   - Include all source code files
   - Include metadata parquet files
   - Create a single executable file

### Runtime Behavior

When a user runs `TigerTag.exe`:
1. PyInstaller extracts bundled files to a temporary directory (first run only)
2. The `launcher.py` script (embedded in the exe) handles path setup
3. The GUI application starts automatically

## File Structure

```
tigertag/
├── launcher.py          # Entry point script (patches paths for frozen exe)
├── tigertag.spec        # PyInstaller configuration
├── build_exe.py         # Build automation script
├── dist/                # Output directory (created during build)
│   └── TigerTag.exe     # The final executable
└── build/               # Build artifacts (can be deleted)
```

## Configuration

### Modifying the Spec File

If you need to customize the build, edit `tigertag.spec`:

- **Add an icon**: Set `icon='path/to/icon.ico'` in the `EXE()` section
- **Show console window**: Change `console=False` to `console=True` (for debugging)
- **Include additional files**: Add entries to the `datas` list
- **Add hidden imports**: Add to the `hiddenimports` list

### Customizing the Executable Name

Edit `tigertag.spec` and change:
```python
name='TigerTag',  # Change this to your desired name
```

## Troubleshooting

### Build Fails

1. **Missing dependencies**: Run `pip install -e .` to install all project dependencies
2. **Missing metadata files**: Ensure `metadata/parquet_files/` contains `.parquet` files
3. **Path errors**: Check that the project structure matches what's expected in the spec file

### Executable Doesn't Run

1. **Check file size**: The exe should be 100-200MB. If it's much smaller, the build may have failed silently
2. **Enable console**: Temporarily set `console=True` in the spec file to see error messages
3. **Test with Python first**: Ensure the application runs correctly when executed with Python:
   ```bash
   python launcher.py
   ```

### Antivirus Warnings

PyInstaller executables are often flagged by antivirus software because they:
- Are self-extracting archives
- May contain obfuscated code

This is normal. Users may need to add an exception for the executable.

## Advanced: Creating a True Installer

If you want a traditional installer (with installation wizard, Start Menu shortcuts, etc.), you can:

1. Build the executable using this process
2. Use a tool like **Inno Setup** or **NSIS** to create an installer that:
   - Installs the exe to Program Files
   - Creates Start Menu shortcuts
   - Adds uninstaller
   - Sets up file associations (if needed)

The bundled executable approach (what we've created) is simpler and usually sufficient.

## Notes

- **File size**: The executable will be large (100-200MB) because it includes Python and all dependencies
- **First launch**: May take a few seconds as files are extracted to a temp directory
- **Portable**: The exe is portable - users can copy it anywhere and run it
- **No installation needed**: Users don't need Python or any dependencies installed

## Support

If you encounter issues:
1. Check the build output for error messages
2. Verify all dependencies are installed
3. Test that the application runs correctly as a Python script first
4. Try building with `console=True` to see runtime errors

