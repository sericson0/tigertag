#!/usr/bin/env python3
"""
Helper script to check FFmpeg installation and PATH configuration.
"""

import subprocess
import sys
import os
from pathlib import Path

def check_ffmpeg_in_path():
    """Check if FFmpeg is in PATH."""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ FFmpeg found in PATH!")
            print(f"Version info (first line): {result.stdout.split(chr(10))[0]}")
            return True
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass
    return False

def find_ffmpeg_common_locations():
    """Search for FFmpeg in common installation locations."""
    common_paths = [
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe"),
        Path(os.path.expanduser("~/ffmpeg/bin/ffmpeg.exe")),
        Path(os.path.expanduser("~/Downloads/ffmpeg/bin/ffmpeg.exe")),
    ]
    
    found_paths = []
    for path in common_paths:
        if path.exists():
            found_paths.append(path)
    
    return found_paths

def main():
    print("=" * 60)
    print("FFmpeg Installation Checker")
    print("=" * 60)
    print()
    
    # Check if in PATH
    if check_ffmpeg_in_path():
        print("\n✓ FFmpeg is properly installed and accessible!")
        return
    
    print("X FFmpeg not found in PATH")
    print()
    
    # Search common locations
    print("Searching common installation locations...")
    found = find_ffmpeg_common_locations()
    
    if found:
        print(f"\n✓ Found FFmpeg in {len(found)} location(s):")
        for path in found:
            print(f"  - {str(path)}")
        print("\nTo add to PATH:")
        print("1. Copy the directory path (e.g., C:/ffmpeg/bin)")
        print("2. Open System Properties → Environment Variables")
        print("3. Edit the 'Path' variable under 'System variables'")
        print("4. Add the directory path")
        print("5. Restart your terminal/IDE")
    else:
        print("\nX FFmpeg not found in common locations")
        print("\nTo install FFmpeg:")
        print("1. Download from: https://ffmpeg.org/download.html")
        print("2. Extract to a folder (e.g., C:/ffmpeg)")
        print("3. Add the 'bin' folder to your system PATH")
        print("4. Restart your terminal/IDE")
    
    print("\n" + "=" * 60)
    print("\nIMPORTANT: After adding FFmpeg to PATH, you MUST:")
    print("  - Close and restart your terminal/IDE")
    print("  - Or restart your computer")
    print("  - PATH changes only take effect in new processes!")

if __name__ == '__main__':
    main()

