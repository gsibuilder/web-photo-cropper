"""
Build script for standalone Windows Setup Installer (Setup_WebPhotoCropper.exe)
"""
import os
import subprocess
import sys

def build_installer():
    print("Building standalone Setup_WebPhotoCropper.exe installer...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Setup_WebPhotoCropper",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon=app_icon.ico",
        "--add-data=dist/WebPhotoCropper;dist/WebPhotoCropper",
        "--add-data=app_icon.ico;.",
        "installer_gui.py"
    ]
    subprocess.check_call(cmd)
    print("Installer build finished! Created: dist/Setup_WebPhotoCropper.exe")

if __name__ == "__main__":
    build_installer()
