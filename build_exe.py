#!/usr/bin/env python
"""
Build script to create the Windows executable for tigertag.
This script installs PyInstaller if needed and builds the executable.
"""
import subprocess
import sys
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed, install if not."""
    try:
        import PyInstaller
        print(f"PyInstaller found: version {PyInstaller.__version__}")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return True

def build_executable():
    """Build the executable using PyInstaller."""
    project_root = Path(__file__).parent
    
    # Check if spec file exists
    spec_file = project_root / "tigertag.spec"
    if not spec_file.exists():
        print(f"Error: {spec_file} not found!")
        return False
    
    # Check if launcher exists
    launcher_file = project_root / "launcher.py"
    if not launcher_file.exists():
        print(f"Error: {launcher_file} not found!")
        return False
    
    print(f"Building executable from {spec_file}...")
    print(f"Project root: {project_root}")
    
    # Run PyInstaller
    try:
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            "--clean",
            str(spec_file)
        ], cwd=str(project_root))
        
        exe_path = project_root / "dist" / "TigerTag.exe"
        if exe_path.exists():
            print(f"\n✓ Build successful!")
            print(f"✓ Executable created at: {exe_path}")
            print(f"\nYou can now distribute {exe_path.name} to users.")
            print("It includes all dependencies and can run without Python installed.")
            return True
        else:
            print(f"\n✗ Build completed but {exe_path} not found!")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed with error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TigerTag Executable Builder")
    print("=" * 60)
    print()
    
    # Check/install PyInstaller
    if not check_pyinstaller():
        print("Failed to install PyInstaller. Exiting.")
        sys.exit(1)
    
    print()
    
    # Build executable
    success = build_executable()
    
    if success:
        print("\n" + "=" * 60)
        print("Build process completed successfully!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("Build process failed. Check errors above.")
        print("=" * 60)
        sys.exit(1)

