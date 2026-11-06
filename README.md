# Smart Account Pro

Smart Account Pro is a Windows desktop accounting application from Shiv Computer.

## Installer

The current installer source builds version **2.0.4**. Run [build_installer.bat](build_installer.bat) to create `output/SmartAccountPro_Setup_2.0.4.exe`.

The installer upgrades an existing installation using its existing install location and data-folder settings. Before upgrading, it copies the existing data folder to Documents; if that safety copy fails, setup stops without updating the app. Accounting databases and backups are kept during upgrades.

## Build

On Windows, install Python 3.8 or newer with the `py` launcher and Inno Setup 6.3 or newer, then run `build_installer.bat`. The script builds for installed Python architectures; the committed installer is 64-bit.

See [README.txt](README.txt) for detailed installation, data-folder, and uninstall information.
