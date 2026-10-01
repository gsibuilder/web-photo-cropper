"""
Modern Windows Setup / Installer Wizard for Web Photo Cropper
"""
import sys
import os
import shutil
import subprocess
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QLabel, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QCheckBox, QProgressBar, QFileDialog, QFrame,
    QMessageBox
)


def create_windows_shortcut(target_path, shortcut_path, icon_path=None, description="", is_chrome=False):
    """Creates a Windows .lnk shortcut using PowerShell."""
    try:
        work_dir = os.path.dirname(target_path) if os.path.isfile(target_path) else target_path
        ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{target_path}'
$Shortcut.WorkingDirectory = '{work_dir}'
$Shortcut.Description = '{description}'
"""
        if icon_path and os.path.exists(icon_path):
            ps_script += f"$Shortcut.IconLocation = '{icon_path}, 0'\n"
        ps_script += "$Shortcut.Save()\n"

        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)
    except Exception as e:
        print(f"Shortcut creation error: {e}")




class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, source_dir, target_dir, create_desktop, create_startmenu, create_chrome):
        super().__init__()
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.create_desktop = create_desktop
        self.create_startmenu = create_startmenu
        self.create_chrome = create_chrome

    def run(self):
        try:
            self.progress.emit(10, "Preparing installation directory...")
            os.makedirs(self.target_dir, exist_ok=True)

            # Linux-specific: install required system packages
            if sys.platform != "win32":
                self.progress.emit(12, "Installing Linux system dependencies...")
                req_path = os.path.join(os.path.dirname(__file__), "linux_requirements.txt")
                if os.path.isfile(req_path):
                    import subprocess
                    subprocess.run(["sudo", "apt-get", "update"], check=True)
                    with open(req_path, "r") as f:
                        packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                    if packages:
                        subprocess.run(["sudo", "apt-get", "install", "-y"] + packages, check=True)
                else:
                    print("Linux requirements file not found:", req_path)

            self.progress.emit(25, "Copying application files...")
            total_files = 0
            for root, dirs, files in os.walk(self.source_dir):
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', '.idea', '.vs']]
                total_files += len(files)

            copied = 0
            for root, dirs, files in os.walk(self.source_dir):
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', '.idea', '.vs']]
                rel_path = os.path.relpath(root, self.source_dir)
                dest_root = os.path.join(self.target_dir, rel_path) if rel_path != "." else self.target_dir
                os.makedirs(dest_root, exist_ok=True)

                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dest_root, file)
                    shutil.copy2(src_file, dst_file)
                    copied += 1
                    pct = 25 + int((copied / max(1, total_files)) * 50)
                    self.progress.emit(pct, f"Installing: {file}")

            exe_path = os.path.join(self.target_dir, "WebPhotoCropper.exe")
            if not os.path.exists(exe_path):
                # If running from source directory
                exe_path = os.path.join(self.target_dir, "main.py")

            # Auto-Detect and Install Chrome Extension if Chrome is present on device
            self.progress.emit(80, "Detecting Chrome and installing extension...")
            ch_installed, ch_path = install_chrome_extension(self.target_dir)
            if ch_installed:
                print(f"Chrome extension auto-configured for: {ch_path}")

            # Shortcuts
            icon_path = os.path.join(self.target_dir, "app_icon.ico")
            self.progress.emit(85, "Creating shortcuts...")
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            if sys.platform == "win32":
                startmenu_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
            else:
                startmenu_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "applications")

            if self.create_desktop:
                shortcut_file = os.path.join(desktop_dir, "Web Photo Cropper.lnk")
                create_windows_shortcut(exe_path, shortcut_file, icon_path, "Web Photo Quick Cropper & Saver")

            if self.create_startmenu:
                shortcut_file = os.path.join(startmenu_dir, "Web Photo Cropper.lnk")
                create_windows_shortcut(exe_path, shortcut_file, icon_path, "Web Photo Quick Cropper & Saver")

            if self.create_chrome:
                chrome_helper_path = os.path.join(self.target_dir, "chrome_bookmark_helper.html")
                chrome_shortcut_file = os.path.join(desktop_dir, "Web Photo Cropper Chrome Helper.lnk")
                create_windows_shortcut(chrome_helper_path, chrome_shortcut_file, icon_path, "Web Photo Cropper - Chrome Helper", is_chrome=True)

            # Create Uninstaller Script
            self.progress.emit(95, "Generating uninstaller...")
            uninstaller_bat = os.path.join(self.target_dir, "Uninstall.bat")
            desktop_link = os.path.join(os.path.expanduser("~"), "Desktop", "Web Photo Cropper.lnk")
            start_link = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs", "Web Photo Cropper.lnk")
            
            with open(uninstaller_bat, "w") as f:
                f.write(f"""@echo off
echo Uninstalling Web Photo Cropper...
del "{desktop_link}" 2>nul
del "{start_link}" 2>nul
echo Cleaning application files...
cd ..
timeout /t 2 /nobreak >nul
rmdir /s /q "{self.target_dir}"
echo Web Photo Cropper has been successfully uninstalled.
pause
""")

            self.progress.emit(100, "Installation complete!")
            self.finished.emit(True, exe_path)
        except Exception as e:
            self.finished.emit(False, str(e))


class InstallerWizard(QWizard):
    def __init__(self, source_dir):
        super().__init__()
        self.source_dir = source_dir
        self.installed_exe = ""
        
        self.setWindowTitle("Web Photo Cropper - Windows Setup (by Corey Kiesel)")
        self.resize(620, 440)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        icon_path = os.path.join(self.source_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.applyStyle()

        self.addPage(self.createWelcomePage())
        self.addPage(self.createDirectoryPage())
        self.addPage(self.createInstallProgressPage())
        self.addPage(self.createFinishPage())

    def applyStyle(self):
        self.setStyleSheet("""
            QWizard {
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Segoe UI', sans-serif;
            }
            QWidget {
                background-color: #0d1117;
                color: #c9d1d9;
                font-size: 13px;
            }
            QLabel {
                color: #c9d1d9;
            }
            QLineEdit {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #f0f6fc;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #c9d1d9;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #30363d;
                border-radius: 6px;
                text-align: center;
                background-color: #161b22;
                color: #ffffff;
                font-weight: bold;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #238636;
                border-radius: 5px;
            }
            QCheckBox {
                spacing: 8px;
            }
        """)

    def createWelcomePage(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Welcome to Web Photo Cropper Setup")
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("📸 Install Web Photo Cropper & Edge Watcher")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #58a6ff;")
        layout.addWidget(title)

        author_badge = QLabel("<b>Created & Developed by:</b> Corey Kiesel")
        author_badge.setStyleSheet("color: #79c0ff; font-size: 13px;")
        layout.addWidget(author_badge)

        desc = QLabel(
            "This wizard will install <b>Web Photo Quick Cropper & Saver</b> on your computer.<br><br>"
            "Features included:<br>"
            "• 🌐 Automatic Microsoft Edge Click-to-Crop integration<br>"
            "• ⚡ Real-time clipboard watcher & auto-sync<br>"
            "• 📐 Freeform and aspect-ratio locked photo cropping<br>"
            "• 🖨️ Native photo printing & PDF export support<br><br>"
            "Click <b>Next</b> to continue."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addStretch()
        return page

    def createDirectoryPage(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Choose Install Location")
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        desc = QLabel("Select the folder where you want to install Web Photo Cropper:")
        layout.addWidget(desc)

        dir_row = QHBoxLayout()
        default_dir = os.path.join(os.path.expanduser("~"), "Programs", "WebPhotoCropper")
        self.txt_dir = QLineEdit(default_dir)
        dir_row.addWidget(self.txt_dir, stretch=1)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browseDir)
        dir_row.addWidget(browse_btn)
        layout.addLayout(dir_row)

        options_group = QFrame()
        options_layout = QVBoxLayout(options_group)
        options_layout.setContentsMargins(0, 10, 0, 0)
        options_layout.setSpacing(8)

        self.chk_desktop = QCheckBox("Create a Desktop Shortcut")
        self.chk_desktop.setChecked(True)
        options_layout.addWidget(self.chk_desktop)

        self.chk_startmenu = QCheckBox("Create a Start Menu Shortcut")
        self.chk_startmenu.setChecked(True)
        options_layout.addWidget(self.chk_startmenu)

        # Chrome shortcut option (desktop)
        self.chk_chrome = QCheckBox("Create a Chrome Desktop Shortcut")
        self.chk_chrome.setChecked(True)
        options_layout.addWidget(self.chk_chrome)

        layout.addWidget(options_group)
        layout.addStretch()
        return page

    def browseDir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Folder", self.txt_dir.text())
        if folder:
            self.txt_dir.setText(os.path.join(folder, "WebPhotoCropper"))

    def createInstallProgressPage(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Installing Web Photo Cropper")
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        self.status_label = QLabel("Click 'Install' below to begin copying files...")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.install_btn = QPushButton("🚀 Install Now")
        self.install_btn.setStyleSheet("background-color: #238636; color: white; font-weight: bold; padding: 10px;")
        self.install_btn.clicked.connect(self.startInstallation)
        layout.addWidget(self.install_btn)

        layout.addStretch()
        return page

    def startInstallation(self):
        self.install_btn.setEnabled(False)
        target_dir = self.txt_dir.text().strip()

        self.worker = InstallWorker(
            self.source_dir,
            target_dir,
            self.chk_desktop.isChecked(),
            self.chk_startmenu.isChecked(),
            self.chk_chrome.isChecked()
        )
        self.worker.progress.connect(self.onInstallProgress)
        self.worker.finished.connect(self.onInstallFinished)
        self.worker.start()

    def onInstallProgress(self, pct, msg):
        self.progress_bar.setValue(pct)
        self.status_label.setText(msg)

    def onInstallFinished(self, success, result):
        if success:
            self.installed_exe = result
            self.status_label.setText("✅ Installation completed successfully! Click 'Next' to finish.")
            self.next()
        else:
            self.install_btn.setEnabled(True)
            QMessageBox.critical(self, "Installation Failed", f"An error occurred during setup:\n{result}")

    def createFinishPage(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Setup Completed")
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("🎉 Installation Complete!")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #7ee787;")
        layout.addWidget(title)

        desc = QLabel(
            "Web Photo Cropper is now ready to use.<br><br>"
            "You can launch it anytime from your Desktop or Start Menu shortcut."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.chk_launch = QCheckBox("🚀 Launch Web Photo Cropper now")
        self.chk_launch.setChecked(True)
        layout.addWidget(self.chk_launch)

        layout.addStretch()
        return page

    def accept(self):
        if hasattr(self, 'chk_launch') and self.chk_launch.isChecked() and self.installed_exe:
            if os.path.exists(self.installed_exe):
                open_path(self.installed_exe)
        super().accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Source directory is current script dir or dist
    dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "WebPhotoCropper")
    if not os.path.exists(dist_dir):
        dist_dir = os.path.dirname(os.path.abspath(__file__))

    wizard = InstallerWizard(dist_dir)
    wizard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
