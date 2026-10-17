; Bss Booster Windows installer, built with Inno Setup 6.
; Compile using build_installer_windows.bat after packaging dist\BssBooster.exe.
#define MyAppName "Bss Booster"
#define MyAppVersion "1.4.0"
#define MyAppPublisher "Bss Booster"
#define MyAppExeName "BssBooster.exe"

[Setup]
; Keep this stable so installing an update replaces the existing application.
AppId={{B9E37C7E-884B-4209-A73E-15CBEAD54B27}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Bss Booster
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist\installer
OutputBaseFilename=BssBoosterSetup
SetupIconFile=assets\bss_booster_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
VersionInfoVersion=1.4.0.0
VersionInfoDescription=Bss Booster Setup

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
