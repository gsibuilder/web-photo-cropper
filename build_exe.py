"""
Build script to compile WebPhotoCropper into a standalone Windows executable.
"""
import os
import subprocess
import sys

def build():
    print("Building WebPhotoCropper standalone executable with PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=WebPhotoCropper",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon=app_icon.ico",
        "--add-data=edge_bookmark_helper.html;.",
        "--add-data=edge_photo_watcher.user.js;.",
        "--add-data=extension;extension",
        "--add-data=app_icon.ico;.",
        "main.py"
    ]
    subprocess.check_call(cmd)
    print("Build finished! Executable located in dist/WebPhotoCropper/WebPhotoCropper.exe")

if __name__ == "__main__":
    build()
