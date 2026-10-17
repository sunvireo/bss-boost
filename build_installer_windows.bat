@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Bss Booster - Windows Setup Builder

echo ============================================
echo       Bss Booster Setup Builder
 echo ============================================
echo.
echo [1/3] Building the BssBooster.exe application...
call "%~dp0build_windows.bat" --no-pause
if errorlevel 1 goto :build_failed
if not exist "dist\BssBooster.exe" goto :build_failed

echo.
echo [2/3] Checking for Inno Setup 6...
call :find_iscc
if defined ISCC goto :compile

echo Inno Setup 6 is needed to produce a proper Windows installer.
echo Download: https://jrsoftware.org/isdl.php
echo.
where winget >nul 2>nul
if errorlevel 1 goto :missing_inno
choice /C YN /M "Try installing Inno Setup automatically with winget"
if errorlevel 2 goto :missing_inno
echo Installing Inno Setup. Windows may request permission.
winget install --id JRSoftware.InnoSetup --exact --source winget --accept-source-agreements --accept-package-agreements
if errorlevel 1 goto :missing_inno
call :find_iscc
if not defined ISCC goto :missing_inno

:compile
echo.
echo [3/3] Packaging BssBoosterSetup.exe...
"%ISCC%" "BssBooster.iss"
if errorlevel 1 goto :installer_failed
if not exist "dist\installer\BssBoosterSetup.exe" goto :installer_failed
echo.
echo ============================================
echo SUCCESS! Your installer is ready:
echo %CD%\dist\installer\BssBoosterSetup.exe
echo ============================================
echo.
echo Double-click BssBoosterSetup.exe to install Bss Booster.
echo You can share this setup file. Users won't need Python or Inno Setup.
echo.
pause
exit /b 0

:find_iscc
set "ISCC="
if defined ProgramFiles(x86) if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
exit /b 0

:missing_inno
echo.
echo Inno Setup was not found. Install Inno Setup 6 from:
echo https://jrsoftware.org/isdl.php
echo Then run build_installer_windows.bat again.
echo Your standalone app may already be at dist\BssBooster.exe.
pause
exit /b 1

:build_failed
echo.
echo Could not build BssBooster.exe. Make sure Python 3.11+
echo is installed, then check the error messages above.
pause
exit /b 1

:installer_failed
echo.
echo Inno Setup could not compile the installer. Check errors above.
pause
exit /b 1
