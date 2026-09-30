"""
Build script for standalone Setup Installer (Setup_WebPhotoCropper)
Supports building installer GUI executable for Windows and Linux.
"""
import os
import subprocess
import sys

def build_installer():
    print(f"Building standalone Setup_WebPhotoCropper installer for {sys.platform}...")
    sep = os.pathsep
    ext = ".exe" if sys.platform == "win32" else ""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Setup_WebPhotoCropper",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon=app_icon.ico",
        f"--add-data=dist/WebPhotoCropper{sep}dist/WebPhotoCropper",
        f"--add-data=app_icon.ico{sep}.",
        "installer_gui.py"
    ]
    subprocess.check_call(cmd)
    print(f"Installer build finished! Created: dist/Setup_WebPhotoCropper{ext}")

if __name__ == "__main__":
    build_installer()
