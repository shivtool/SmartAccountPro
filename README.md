# Smart Account Pro

Smart Account Pro is a Windows desktop accounting application from Shiv Computer.

## Release

Version **2.0.1** installer: [Download SmartAccountPro_Setup_2.0.1.exe](output/SmartAccountPro_Setup_2.0.1.exe).

The installer upgrades an existing installation using its existing install location and data-folder settings. Accounting databases and backups are kept during upgrades. Back up important data before installing any release.

## Build

On Windows, install Python 3.8 or newer with the `py` launcher and Inno Setup 6.3 or newer, then run `build_installer.bat`. The script builds for installed Python architectures; the committed installer is 64-bit.

See [README.txt](README.txt) for detailed installation, data-folder, and uninstall information.
