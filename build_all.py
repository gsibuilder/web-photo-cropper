"""
Unified build script to compile both the main application executable
and the standalone setup installer.
"""
import os
import sys
import subprocess

def main():
    print("=== Step 1/2: Building Standalone Executable ===")
    from build_exe import build as build_app
    build_app()

    print("\n=== Step 2/2: Building Setup Installer ===")
    from build_installer import build_installer as build_inst
    build_inst()

    ext = ".exe" if sys.platform == "win32" else ""
    print("\n✅ Build complete!")
    print(f"App Bundle: dist/WebPhotoCropper/")
    print(f"Standalone Installer: dist/Setup_WebPhotoCropper{ext}")

if __name__ == "__main__":
    main()
