; =====================================================================
;  Smart Account Pro  -  Professional Installer  (Shiv Computer)
;  Inno Setup 6.3 ya naya (6.x / 7.x) se compile hota hai.
;  Compile:  build_installer.bat  (ya Inno Setup mein is file ko khol kar F9)
;  File ko UTF-8 (BOM ke saath) hi save rakhein, warna Hindi text bigad jayega.
; =====================================================================
#define AppName      "Smart Account Pro"
#define AppExe       "SmartAccountPro.exe"
#define AppPublisher "Shiv Computer"
#ifndef AppVersion
  #define AppVersion "2.0.4"
#endif
#define AppId        "{{6B3E2F0A-5D7C-4E1B-9A41-5A7C0C2E9D11}"
#define Dist64       "build\x64\sap.dist"
#define Dist32       "build\x86\sap.dist"

#if FileExists("build\x64\sap.dist\SmartAccountPro.exe")
  #define Has64
#endif
#if FileExists("build\x86\sap.dist\SmartAccountPro.exe")
  #define Has32
#endif
#if !defined(Has64) && !defined(Has32)
  #error "Pehle exe build karein: build_installer.bat chalayein (build\x64\sap.dist ya build\x86\sap.dist nahi mila)."
#endif

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright=Copyright (c) {#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=no
DisableWelcomePage=no
UsePreviousAppDir=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
OutputDir=output
OutputBaseFilename=SmartAccountPro_Setup_{#AppVersion}
SetupIconFile=assets\app.ico
WizardStyle=modern
WizardImageFile=assets\wiz_large.bmp,assets\wiz_large_2x.bmp
WizardSmallImageFile=assets\wiz_small.bmp,assets\wiz_small_2x.bmp
LicenseFile=assets\license.txt
Compression=lzma2/max
SolidCompression=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=no
SetupLogging=yes
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}.0
#ifdef Has64
ArchitecturesInstallIn64BitMode=x64compatible
#endif
#ifndef Has32
ArchitecturesAllowed=x64compatible
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to {#AppName} Setup
WelcomeLabel2=This wizard will install [name/ver] on your computer.%n%nयह विज़ार्ड आपके कंप्यूटर पर [name/ver] इंस्टॉल करेगा।%n%nBefore continuing, please close Smart Account Pro if it is running. Your accounts data is never touched during an upgrade.
FinishedHeadingLabel=Setup complete
FinishedLabel=[name] has been installed on your computer.%n%nइंस्टॉलेशन पूरी हुई।

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Dirs]
Name: "{code:DataDir}"; Permissions: users-modify; Flags: uninsneveruninstall; Check: IsAdminInstallMode
Name: "{code:DataDir}"; Flags: uninsneveruninstall; Check: not IsAdminInstallMode

[Files]
#ifdef Has64
Source: "{#Dist64}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: Is64BitInstallMode
#endif
#ifdef Has32
Source: "{#Dist32}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: not Is64BitInstallMode
#endif
Source: "assets\app.ico"; DestDir: "{app}"; DestName: "logo.ico"; Flags: ignoreversion
Source: "assets\logo.png"; DestDir: "{app}"; DestName: "logo.png"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{autoprograms}\{#AppName}\Open Data Folder"; Filename: "{sys}\explorer.exe"; Parameters: """{code:DataDir}"""
Name: "{autoprograms}\{#AppName}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\ShivComputer"; Flags: uninsdeletekeyifempty
Root: HKA; Subkey: "Software\ShivComputer\SmartAccountPro"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\ShivComputer\SmartAccountPro"; ValueType: string; ValueName: "DataDir"; ValueData: "{code:DataDir}"
Root: HKA; Subkey: "Software\ShivComputer\SmartAccountPro"; ValueType: string; ValueName: "Version"; ValueData: "{#AppVersion}"

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent; Check: MigrationSucceeded

[UninstallDelete]
Type: files; Name: "{app}\sap_data_dir.txt"
Type: dirifempty; Name: "{app}"

[Code]
const
  RegCompany = 'Software\ShivComputer\SmartAccountPro';
  AppExeName = '{#AppExe}';
  DataFolderName = 'SmartAccountPro';

var
  PrevPage: TWizardPage;
  HavePrev: Boolean;
  PrevVersion, PrevDataDir, PrevAppDir: String;
  PreUpgradeBackupPath: String;
  UnDataDir: String;
  UnRemoveData, UnBackup: Boolean;
  LegacyMigrationOk: Boolean;

// ---------------------------------------------------------------- helpers
function UninstKey: String;
begin
  Result := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1');
end;

function DefaultDataDir: String;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{commonappdata}\' + DataFolderName)
  else
    Result := ExpandConstant('{localappdata}\' + DataFolderName);
end;

// DataDir (code constant): data hamesha install folder se alag; upgrade mein purani jagah hi rehta hai
function DataDir(Param: String): String;
begin
  if (PrevDataDir <> '') and DirExists(PrevDataDir) then
    Result := PrevDataDir
  else
    Result := DefaultDataDir;
end;

function SafeDataDir(D: String): Boolean;
begin
  D := RemoveBackslash(D);
  Result := (Length(D) > 12) and SameText(ExtractFileName(D), DataFolderName);
end;

function HasParam(const Name: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), Name) = 0 then
    begin
      Result := True;
      Exit;
    end;
end;

procedure KillApp;
var
  RC: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM ' + AppExeName, '', SW_HIDE, ewWaitUntilTerminated, RC);
end;

function BackupFolder(const Src: String; var Dest: String): Boolean;
var
  RC: Integer;
begin
  Dest := ExpandConstant('{userdocs}\SmartAccountPro_Backup_') + GetDateTimeString('yyyymmdd-hhnnss', #0, #0);
  Result := Exec(ExpandConstant('{sys}\xcopy.exe'),
    '"' + RemoveBackslash(Src) + '" "' + Dest + '" /E /I /Y /Q /H /K', '', SW_HIDE, ewWaitUntilTerminated, RC)
    and (RC <= 1);
end;

// ---------------------------------------------------------------- purana version dhoondhna
function TryRoot(Root: Integer): Boolean;
var
  S: String;
begin
  Result := False;
  if not RegQueryStringValue(Root, UninstKey, 'UninstallString', S) then Exit;
  if not RegQueryStringValue(Root, UninstKey, 'DisplayVersion', PrevVersion) then PrevVersion := '?';
  if not RegQueryStringValue(Root, UninstKey, 'InstallLocation', PrevAppDir) then PrevAppDir := '';
  if not RegQueryStringValue(Root, RegCompany, 'DataDir', PrevDataDir) then PrevDataDir := '';
  Result := FileExists(RemoveQuotes(S));
end;

function FindPrevious: Boolean;
begin
  Result := True;
  if IsWin64 and TryRoot(HKLM64) then Exit;
  if TryRoot(HKLM32) then Exit;
  if TryRoot(HKCU) then Exit;
  Result := False;
end;

// ---------------------------------------------------------------- wizard page
procedure InitializeWizard;
var
  Info: TNewStaticText;
  D: String;
begin
  HavePrev := FindPrevious;
  D := DataDir('');
  if not HavePrev and not (FileExists(D + '\sap.db') or FileExists(D + '\smart_account_data.json')) then Exit;
  if HavePrev then
    PrevPage := CreateCustomPage(wpWelcome, 'Existing installation found / पुराना version मिला',
      '{#AppName} ' + PrevVersion + ' is already installed. This setup will upgrade it and keep your accounting data.')
  else
    PrevPage := CreateCustomPage(wpWelcome, 'Existing data found / पुराना data मिला',
      'Existing Smart Account Pro accounting data was found. This setup will keep it and create a safety copy.');
  Info := TNewStaticText.Create(PrevPage);
  Info.Parent := PrevPage.Surface;
  Info.Left := 0;
  Info.Top := 0;
  Info.Width := PrevPage.SurfaceWidth;
  Info.AutoSize := True;
  Info.WordWrap := True;
  if HavePrev then
    Info.Caption := 'Installed: {#AppName} ' + PrevVersion + '   ->   New: {#AppVersion}' + #13#10 +
                    'UPGRADE: Existing installation and data folder will be kept.' + #13#10 +
                    'DATA: ' + D + #13#10
  else
    Info.Caption := 'DATA: Existing accounting data was found.' + #13#10 +
                    'DATA FOLDER: ' + D + #13#10;
  Info.Caption := Info.Caption +
                  'SAFETY: After the app closes, a copy is saved in Documents before files are updated.' + #13#10 +
                  'If that safety copy cannot be created, setup stops without updating the app.' + #13#10#13#10 +
                  'Your accounts, settings, and automatic backups are not removed.' + #13#10 +
                  'Agar program khula hai, installer pehle use safely close karne ko kahega.';
end;

// ---------------------------------------------------------------- install ke baad
procedure MigrateLegacyData;
var
  D, S: String;
  Copied: Boolean;
begin
  D := DataDir('');
  S := ExpandConstant('{app}');
  if (PrevAppDir <> '') and
     (FileExists(PrevAppDir + '\sap.db') or FileExists(PrevAppDir + '\smart_account_data.json')) then
    S := PrevAppDir;
  if FileExists(S + '\sap.db') and not FileExists(D + '\sap.db') then
  begin
    Copied := CopyFile(S + '\sap.db', D + '\sap.db', False);
    if Copied and FileExists(S + '\sap.db-wal') then
      Copied := CopyFile(S + '\sap.db-wal', D + '\sap.db-wal', False);
    if Copied and FileExists(S + '\smart_account_data.json') and not FileExists(D + '\smart_account_data.json') then
      Copied := CopyFile(S + '\smart_account_data.json', D + '\smart_account_data.json', False);
    if Copied then
    begin
      RenameFile(S + '\sap.db', S + '\sap.db.migrated');
    end
    else
    begin
      LegacyMigrationOk := False;
      DeleteFile(D + '\sap.db');
      DeleteFile(D + '\sap.db-wal');
      DeleteFile(D + '\smart_account_data.json');
      MsgBox('Purana data copy nahi ho saka. Purani file ko surakshit rakha gaya hai:' + #13#10 +
             S + '\sap.db' + #13#10#13#10 +
             'Installer band karke support se sampark karein; naya app abhi launch na karein.',
             mbError, MB_OK);
    end;
  end
  else if FileExists(S + '\smart_account_data.json') and
          not FileExists(D + '\sap.db') and not FileExists(D + '\smart_account_data.json') then
  begin
    if not CopyFile(S + '\smart_account_data.json', D + '\smart_account_data.json', False) then
    begin
      LegacyMigrationOk := False;
      MsgBox('Purana data copy nahi ho saka. Purani file ko surakshit rakha gaya hai:' + #13#10 +
             S + '\smart_account_data.json' + #13#10#13#10 +
             'Installer band karke support se sampark karein; naya app abhi launch na karein.',
             mbError, MB_OK);
    end;
  end;
end;

function MigrationSucceeded: Boolean;
begin
  Result := LegacyMigrationOk;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  L: TArrayOfString;
  D: String;
begin
  if CurStep = ssInstall then
  begin
    D := DataDir('');
    if (FileExists(D + '\sap.db') or FileExists(D + '\smart_account_data.json')) and
       not BackupFolder(D, PreUpgradeBackupPath) then
      RaiseException('The existing data could not be backed up. Setup stopped before updating the app.' +
                     ' Original data folder: ' + D + #13#10#13#10 +
                     'Make space in Documents or check its permissions, then run setup again.');
    Exit;
  end;
  if CurStep = ssPostInstall then
  begin
    LegacyMigrationOk := True;
    MigrateLegacyData;
    SetArrayLength(L, 1);
    L[0] := DataDir('');
    if not SaveStringsToUTF8File(ExpandConstant('{app}\sap_data_dir.txt'), L, False) then
    begin
      LegacyMigrationOk := False;
      MsgBox('Data folder ki setting save nahi ho saki. App ko launch nahi kiya gaya.' + #13#10#13#10 +
             'Installer dobara chalayein ya support se sampark karein.',
             mbError, MB_OK);
    end;
  end;
  if (CurStep = ssDone) and (PreUpgradeBackupPath <> '') then
    SuppressibleMsgBox('A safety copy of your existing data was saved before the upgrade:' + #13#10 +
                       PreUpgradeBackupPath,
                       mbInformation, MB_OK, IDOK);
end;

// ---------------------------------------------------------------- uninstall
function InitializeUninstall: Boolean;
begin
  Result := True;
  UnRemoveData := False;
  UnBackup := True;
  if not RegQueryStringValue(HKA, RegCompany, 'DataDir', UnDataDir) then
    UnDataDir := DefaultDataDir;
  if HasParam('/REMOVEDATA') then
  begin
    UnRemoveData := True;
    UnBackup := not HasParam('/NOBACKUP');
  end
  else if HasParam('/KEEPDATA') or UninstallSilent then
    UnRemoveData := False
  else if DirExists(UnDataDir) then
  begin
    if MsgBox('Kya aap apna accounts data bhi hatana chahte hain?' + #13#10 + #13#10 +
              'YES  =  data bhi hatao' + #13#10 + 'NO   =  data rakho (recommended)' + #13#10 + #13#10 +
              'Data folder: ' + UnDataDir, mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    begin
      UnRemoveData := True;
      UnBackup := MsgBox('Hatane se pehle data ki backup copy Documents folder mein rakhein?',
                         mbConfirmation, MB_YESNO) = IDYES;
    end;
  end;
  KillApp;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Bk: String;
begin
  if CurUninstallStep <> usPostUninstall then Exit;
  if not UnRemoveData then Exit;
  if not (SafeDataDir(UnDataDir) and DirExists(UnDataDir)) then Exit;
  if UnBackup then
    if not BackupFolder(UnDataDir, Bk) then
    begin
      SuppressibleMsgBox('Backup nahi ban saka, isliye data nahi hataya gaya: ' + UnDataDir, mbError, MB_OK, IDOK);
      Exit;
    end;
  DelTree(UnDataDir, True, True, True);
  if Bk <> '' then
    SuppressibleMsgBox('Data hat gaya. Backup copy yahan hai:' + #13#10 + Bk, mbInformation, MB_OK, IDOK);
end;
