[Setup]
; ==============================================================================
; BRANDING & IDENTIFICATION
; ==============================================================================
AppId={{F03943A6-C152-4BC2-995C-6ED781A8EF28}
AppName=AI Suite
AppVersion=1.0.0
AppVerName=AI Suite v1.0.0
AppPublisher=AI Suite Project
AppPublisherURL=https://github.com/AI-Suite-Project
AppSupportURL=https://github.com/AI-Suite-Project/issues
AppUpdatesURL=https://github.com/AI-Suite-Project/releases

; VersionInfo metadata for the compiled installer executable
VersionInfoVersion=1.0.0.0
VersionInfoCompany=AI Suite Project
VersionInfoDescription=AI Suite Setup
VersionInfoProductName=AI Suite

; ==============================================================================
; INSTALLATION DIRECTORY & PRIVILEGES
; ==============================================================================
; {autopf} maps to "Program Files" or "Program Files (x86)" depending on OS and bitness
DefaultDirName={autopf}\AI Suite
DisableProgramGroupPage=yes
PrivilegesRequired=lowest

; ==============================================================================
; WINDOWS COMPATIBILITY & ARCHITECTURE
; ==============================================================================
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no

; ==============================================================================
; OUTPUT & COMPRESSION
; ==============================================================================
OutputDir=.\installers
OutputBaseFilename=AI-Suite-1.0.0-Setup
Compression=lzma2
SolidCompression=yes

; ==============================================================================
; ICONS & VISUALS
; ==============================================================================
SetupIconFile=assets\logo\app_icon.ico
UninstallDisplayIcon={app}\AI Suite.exe

[Tasks]
; Optional checkbox on the "Select Additional Tasks" wizard page
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Packages the entire compiled output from PyInstaller (exe, _internal, assets, models)
Source: "dist\AI Suite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut
Name: "{autoprograms}\AI Suite"; Filename: "{app}\AI Suite.exe"; IconFilename: "{app}\AI Suite.exe"
; Desktop shortcut (linked to the optional task)
Name: "{autodesktop}\AI Suite"; Filename: "{app}\AI Suite.exe"; Tasks: desktopicon; IconFilename: "{app}\AI Suite.exe"

[Run]
; Checkbox on the final wizard page to launch the app
Filename: "{app}\AI Suite.exe"; Description: "Launch AI Suite"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; ==============================================================================
; NORMAL UNINSTALLATION POLICY
; ==============================================================================
; What is REMOVED:
; - Application program files (the executable, bundled dependencies, assets)
; - Temporary runtime files and generated cache
; - Application diagnostic logs
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{localappdata}\AISuite\logs"
Type: filesandordirs; Name: "{localappdata}\AISuite\cache"

; What is PRESERVED (to prevent data loss for normal users):
; - User configuration ({localappdata}\AISuite\settings.json)
; - Secrets and API keys ({localappdata}\AISuite\secrets.json)
; - Downloaded AI models ({localappdata}\AISuite\models)
; - Vector databases / memory ({localappdata}\AISuite\memory)
; - User-specific data (faces, profiles)

[Code]
var
  DownloadPage: TDownloadWizardPage;

function VCRedistInstalled(): Boolean;
var
  bld: Cardinal;
begin
  Result := False;
  if RegQueryDWordValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Bld', bld) then begin
    Result := True;
  end;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
begin
  if (CurPageID = wpReady) and (not VCRedistInstalled()) then begin
    DownloadPage.Clear;
    DownloadPage.Add('https://aka.ms/vs/17/release/vc_redist.x64.exe', 'vc_redist.x64.exe', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
        Exec(ExpandConstant('{tmp}\vc_redist.x64.exe'), '/install /quiet /norestart', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      except
        MsgBox('Failed to download Visual C++ Redistributable. You may need to install it manually.', mbError, MB_OK);
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
  Result := True;
end;
