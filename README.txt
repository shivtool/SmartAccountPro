SMART ACCOUNT PRO - INSTALLER KIT  (Shiv Computer)
==================================================

KAISE BANAYEIN  (Windows PC par, sirf ek baar setup)
1. Python 3.8+ install karein (py launcher ke saath). 32-bit support chahiye to 32-bit Python bhi.
   Windows 7/8 par chalana ho to Python 3.8 se build karein.
2. Inno Setup 6.3 ya naya install karein: https://jrsoftware.org/isdl.php
3. Visual Studio ya MinGW pehle se na ho to Nuitka khud MinGW download kar leta hai (internet chahiye).
4. Is folder mein build_installer.bat par double-click karein.
   Result:  output\SmartAccountPro_Setup_<version>.exe   (available 32-bit / 64-bit builds ke liye)

LOGO / BRANDING
- Apna logo.png (ya logo.ico) is folder mein rakhein, phir build_installer.bat chalayein.
  Wahi app icon, installer icon, wizard image aur app ke andar ka logo banega.
- Bina logo ke default violet "SAP" logo use hota hai.

INSTALLER KYA KARTA HAI
- Install folder: Program Files\Smart Account Pro (all users) ya sirf aapke liye (install ke time poochta hai).
- DATA alag folder mein rehta hai, isliye upgrade/uninstall mein safe:
    all-users install : C:\ProgramData\SmartAccountPro
    per-user install  : %LOCALAPPDATA%\SmartAccountPro
  (sap.db, roz ke auto-backup, error log). App ke Settings mein "Data folder" aur "Kholen" button hai.
- Naya installer purane version ko upgrade karta hai: wahi App ID aur purana install folder use hota hai.
  Upgrade ke dauran accounts database, auto-backup aur data folder delete nahi hote.
- Upgrade se pehle existing data folder ki safety copy Documents mein banti hai. Copy na ban sake
  (jaise disk space ya permissions ki kami) to installer upgrade rok deta hai; original data wahi rehta hai.
- Purana data folder registry mein milne par wahi reuse hota hai. Bahut purane portable install
  mein `sap.db` ya JSON ho to pehle data folder mein copy hoti hai; source copy migration ke baad bhi rehti hai.
- Upgrade wizard mein clean-install ya data-delete option nahi hai. Data hatana ho to uninstall ke
  waqt alag se poochha jayega; default NO data ko rakhta hai, aur deletion se pehle backup ka option hai.
- Desktop shortcut (optional), Start Menu shortcuts, "Open Data Folder" shortcut.

SILENT / LAN DEPLOYMENT
  Upgrade   : SmartAccountPro_Setup_2.0.4.exe /VERYSILENT /NORESTART          (purana data rakhta hai)
  Uninstall : "...\unins000.exe" /VERYSILENT                                    (data rakhta hai)
              "...\unins000.exe" /VERYSILENT /REMOVEDATA                        (data hatata hai, backup ke saath)
              "...\unins000.exe" /VERYSILENT /REMOVEDATA /NOBACKUP              (bina backup)
  Sirf is user ke liye: /CURRENTUSER      Sabke liye: /ALLUSERS

DATA FOLDER BADALNA (advanced)
- Environment variable SAP_DATA_DIR set karein, ya install folder ki sap_data_dir.txt mein path likhein.

SMARTSCREEN / ANTIVIRUS
- Unsigned exe par Windows SmartScreen "Unknown publisher" dikha sakta hai (More info > Run anyway).
  Code-signing certificate ho to installer.iss ke [Setup] mein SignTool line jodein.

FILES
  sap.py              app (data-folder logic ke saath)
  installer.iss       Inno Setup script
  build_installer.bat Nuitka + Inno build
  assets\             icon, wizard images, license, make_assets.py
