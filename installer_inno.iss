; Inno Setup Script for Web Photo Cropper
[Setup]
AppName=Web Photo Cropper
AppVersion=1.0
AppPublisher=Corey Kiesel
DefaultDirName={autopf}\WebPhotoCropper
DefaultGroupName=Web Photo Cropper
OutputDir=dist
OutputBaseFilename=WebPhotoCropper_InnoSetup
Compression=lzma2/max
SolidCompression=yes
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\WebPhotoCropper.exe
WizardStyle=modern

[Files]
Source: "dist\WebPhotoCropper\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Web Photo Cropper"; Filename: "{app}\WebPhotoCropper.exe"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\Web Photo Cropper"; Filename: "{app}\WebPhotoCropper.exe"; IconFilename: "{app}\app_icon.ico"

[Run]
Filename: "{app}\WebPhotoCropper.exe"; Description: "Launch Web Photo Cropper"; Flags: nowait postinstall skipifsilent
