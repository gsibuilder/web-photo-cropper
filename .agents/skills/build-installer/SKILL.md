---
name: build-installer
description: >-
  Builds standalone executables and setup installer packages for WebPhotoCropper
  on both Windows (.exe / Setup_WebPhotoCropper.exe) and Linux platforms.
  Use this skill whenever asked to build, compile, or package the application or installer.
---

# WebPhotoCropper Build & Installer Agent Skill

This skill defines the procedures to compile WebPhotoCropper into standalone executables and self-contained GUI installers for Windows and Linux.

## Workflows

### 1. Build Everything (Application + Installer)
To compile both the application bundle and the standalone GUI setup installer:

```bash
python3 build_all.py
```

### 2. Build Application Executable Only
To compile only the PyInstaller application bundle:

```bash
python3 build_exe.py
```
Output artifact: `dist/WebPhotoCropper/`

### 3. Build Setup Installer Only
To compile the standalone setup wizard (`Setup_WebPhotoCropper`):

```bash
python3 build_installer.py
```
Output artifact: `dist/Setup_WebPhotoCropper` (`.exe` on Windows)

## Included Assets & Packaging
All builds automatically package the following core assets:
- `main.py` & `installer_gui.py`
- `edge_bookmark_helper.html` & `chrome_bookmark_helper.html`
- `edge_photo_watcher.user.js`
- `extension/` directory
- `app_icon.ico`
- `linux_requirements.txt`

## Verification Steps
After building, verify artifacts:
- Linux application binary: `dist/WebPhotoCropper/WebPhotoCropper`
- Linux installer binary: `dist/Setup_WebPhotoCropper`
- Windows app executable: `dist/WebPhotoCropper/WebPhotoCropper.exe`
- Windows installer setup: `dist/Setup_WebPhotoCropper.exe`
