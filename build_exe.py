"""
Build script to compile WebPhotoCropper into a standalone executable.
Supports both Windows (.exe) and Linux platforms.
"""
import os
import subprocess
import sys

def build():
    print(f"Building WebPhotoCropper standalone executable for {sys.platform} with PyInstaller...")
    sep = os.pathsep
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=WebPhotoCropper",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon=app_icon.ico",
        f"--add-data=edge_bookmark_helper.html{sep}.",
        f"--add-data=chrome_bookmark_helper.html{sep}.",
        f"--add-data=edge_photo_watcher.user.js{sep}.",
        f"--add-data=extension{sep}extension",
        f"--add-data=app_icon.ico{sep}.",
        f"--add-data=linux_requirements.txt{sep}.",
        "main.py"
    ]
    subprocess.check_call(cmd)
    ext = ".exe" if sys.platform == "win32" else ""
    print(f"Build finished! Executable located in dist/WebPhotoCropper/WebPhotoCropper{ext}")

if __name__ == "__main__":
    build()
