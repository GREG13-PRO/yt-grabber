; Inno Setup script for the YT Grabber Windows installer.
; Packages the PyInstaller onedir output (dist\YT Grabber\) into a setup exe
; with Start Menu + optional desktop shortcut and an uninstaller.
;
; Build:  ISCC.exe /DMyAppVersion=0.1.2 /DRepoRoot=C:\path\to\repo packaging\windows_installer.iss
; The CI workflow passes these defines automatically.

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef RepoRoot
  #define RepoRoot "."
#endif
#define MyAppName "YT Grabber"
#define MyAppExeName "YT Grabber.exe"

[Setup]
AppId={{7B3D9E4A-5C21-4F8B-9A6E-2D1C8F0E5B47}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=YT Grabber
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputBaseFilename=YT-Grabber-Windows-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; lowest = install per-user without a UAC/admin prompt (the app is unsigned).
PrivilegesRequired=lowest
SourceDir={#RepoRoot}
OutputDir=Output

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\YT Grabber\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
