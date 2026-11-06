@echo off
setlocal EnableExtensions
cd /d "%~dp0"
rem ============================================================
rem  Smart Account Pro - EXE (Nuitka) + Setup.exe (Inno Setup)
rem  Version badalne ke liye neeche APPVER badlein.
rem ============================================================
set "APPVER=2.0.4"
set "NFLAGS=--standalone --enable-plugin=tk-inter --windows-console-mode=disable --windows-icon-from-ico=assets\app.ico --output-filename=SmartAccountPro.exe --company-name="Shiv Computer" --product-name="Smart Account Pro" --file-description="Smart Account Pro" --file-version=%APPVER%.0 --product-version=%APPVER%.0 --copyright="Copyright (c) Shiv Computer" --assume-yes-for-downloads"

set "ISCC="
for %%P in (
  "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
  "%ProgramFiles%\Inno Setup 6\ISCC.exe"
  "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
  "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"
  "%ProgramFiles%\Inno Setup 7\ISCC.exe"
  "%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe"
) do if not defined ISCC if exist %%P set "ISCC=%%~P"
if not defined ISCC (
  echo [ERROR] Inno Setup nahi mila. https://jrsoftware.org/isdl.php se Inno Setup 6.3+ install karke dobara chalayein.
  goto :fail
)

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher "py" nahi mila. python.org se Python 3.8+ install karein ^(Add to PATH / py launcher ke saath^).
  goto :fail
)

set "HAS64=0"
set "HAS32=0"
py -3-64 -c "import sys" >nul 2>nul && set "HAS64=1"
py -3-32 -c "import sys" >nul 2>nul && set "HAS32=1"
if "%HAS64%%HAS32%"=="00" (
  echo [ERROR] Na 64-bit na 32-bit Python mila.
  goto :fail
)

echo.
echo === 1/4  Branding assets ===
if "%HAS64%"=="1" (py -3-64 -m pip install --upgrade pillow >nul 2>nul & py -3-64 assets\make_assets.py) else (py -3-32 -m pip install --upgrade pillow >nul 2>nul & py -3-32 assets\make_assets.py)
if errorlevel 1 goto :fail

if "%HAS64%"=="1" (
  echo.
  echo === 2/4  64-bit EXE ^(Nuitka^) - pehli baar 10-20 minute lag sakte hain ===
  py -3-64 -m pip install --upgrade nuitka ordered-set zstandard pillow
  if exist build\x64 rmdir /s /q build\x64
  py -3-64 -m nuitka %NFLAGS% --output-dir=build\x64 sap.py
  if errorlevel 1 goto :fail
)
if "%HAS32%"=="1" (
  echo.
  echo === 3/4  32-bit EXE ^(Nuitka^) ===
  py -3-32 -m pip install --upgrade nuitka ordered-set zstandard pillow
  if exist build\x86 rmdir /s /q build\x86
  py -3-32 -m nuitka %NFLAGS% --output-dir=build\x86 sap.py
  if errorlevel 1 goto :fail
) else (
  echo.
  echo [NOTE] 32-bit Python nahi mila - installer sirf 64-bit Windows ke liye banega.
  echo        32-bit support ke liye 32-bit Python install karke yeh file dobara chalayein.
)

echo.
echo === 4/4  Setup.exe ^(Inno Setup^) ===
"%ISCC%" /DAppVersion=%APPVER% installer.iss
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo  TAIYAR:  output\SmartAccountPro_Setup_%APPVER%.exe
echo ============================================================
explorer output
pause
exit /b 0

:fail
echo.
echo [FAILED] Upar ka error padhein. Build rok diya gaya.
pause
exit /b 1
