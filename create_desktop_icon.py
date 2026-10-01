"""
Utility script to create a Windows Desktop shortcut with icon for WebPhotoCropper.
"""
import os
import sys
import subprocess

def create_desktop_shortcut():
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(repo_dir, "main.py")
    icon_path = os.path.join(repo_dir, "app_icon.ico")
    
    # Check for standalone exe in dist if compiled, otherwise pythonw / main.py
    dist_exe = os.path.join(repo_dir, "dist", "WebPhotoCropper", "WebPhotoCropper.exe")
    use_exe = os.path.exists(dist_exe)

    # Find desktop paths (standard + OneDrive desktop if applicable)
    desktops = []
    
    try:
        ps_cmd = "[Environment]::GetFolderPath('Desktop')"
        res = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True).strip()
        if res and os.path.exists(res) and res not in desktops:
            desktops.append(res)
    except Exception:
        pass

    user_desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.exists(user_desktop) and user_desktop not in desktops:
        desktops.append(user_desktop)

    onedrive_desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
    if os.path.exists(onedrive_desktop) and onedrive_desktop not in desktops:
        desktops.append(onedrive_desktop)

    if not desktops:
        print("Error: Could not locate Desktop folder.")
        return False

    if use_exe:
        target = dist_exe
        args = ""
    else:
        python_dir = os.path.dirname(sys.executable)
        pythonw = os.path.join(python_dir, "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        target = pythonw
        args = main_py

    created = 0
    for desktop in desktops:
        shortcut_file = os.path.join(desktop, "Web Photo Cropper.lnk")
        
        # Build PowerShell shortcut creation script
        ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_file}')
$Shortcut.TargetPath = '{target}'
$Shortcut.Arguments = '"{args}"'
$Shortcut.WorkingDirectory = '{repo_dir}'
$Shortcut.Description = 'Web Photo Quick Cropper & Saver'
"""
        if os.path.exists(icon_path):
            ps_script += f"$Shortcut.IconLocation = '{icon_path}, 0'\n"
        ps_script += "$Shortcut.Save()\n"

        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)
            print(f"[OK] Created desktop icon shortcut at: {shortcut_file}")
            created += 1
        except Exception as e:
            print(f"[ERROR] Failed to create shortcut at {shortcut_file}: {e}")

    return created > 0

if __name__ == "__main__":
    success = create_desktop_shortcut()
    if success:
        print("\nDesktop icon successfully created!")
    else:
        sys.exit(1)
