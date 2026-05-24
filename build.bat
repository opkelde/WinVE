@echo off
echo ========================================
echo      WinVE Ultimate Build Script
echo ========================================
echo.

:: Check if virtual environment is activated, or if packages are installed globally
set "HAS_PACKAGES=0"
if defined VIRTUAL_ENV (
    set "HAS_PACKAGES=1"
    set "SITE_PACKAGES=venv\Lib\site-packages"
) else (
    :: Try to get site-packages path from global python/py
    for /f "delims=" %%i in ('py -c "import os, openwakeword; print(os.path.abspath(os.path.dirname(openwakeword.__path__[0])))" 2^>nul') do (
        set "SITE_PACKAGES=%%i"
        set "HAS_PACKAGES=1"
    )
)

if "%HAS_PACKAGES%"=="0" (
    echo ERROR: Required packages not found!
    echo Please activate virtual environment or install required packages.
    pause
    exit /b 1
)

:: Step 1: Clean up old builds
echo [1/5] Cleaning up old builds...
if exist "dist" (
    echo   Removing dist folder...
    rmdir /s /q "dist"
)
if exist "build" (
    echo   Removing build folder...
    rmdir /s /q "build"
)
if exist "inno\WinVE-Setup.exe" (
    echo   Removing old installer...
    del /q "inno\WinVE-Setup.exe"
)
if exist "*.spec" (
    echo   Removing old spec files...
    del /q "*.spec"
)
echo   Cleanup complete!
echo.

:: Step 2: Build with PyInstaller
echo [2/5] Building application with PyInstaller...
echo   This may take several minutes...
py -m PyInstaller --name "WinVE" ^
    --noconsole ^
    --additional-hooks-dir "pyinstaller_hooks" ^
    --icon "img/icon.ico" ^
    --add-data "frontend;frontend" ^
    --add-data "sound;sound" ^
    --add-data "img;img" ^
    --add-data "models;models" ^
    --add-data "%SITE_PACKAGES%\openwakeword;openwakeword" ^
    --add-data "%SITE_PACKAGES%\onnxruntime\capi\*;onnxruntime/capi/" ^
    --hidden-import "openwakeword" ^
    --hidden-import "openwakeword.model" ^
    --hidden-import "openwakeword.utils" ^
    --hidden-import "webrtcvad" ^
    --hidden-import "pystray" ^
    --hidden-import "PIL" ^
    --hidden-import "numpy" ^
    --hidden-import "scipy" ^
    --hidden-import "onnxruntime" ^
    --hidden-import "sounddevice" ^
    --hidden-import "soundfile" ^
    --hidden-import "flet" ^
    --hidden-import "websockets" ^
    --hidden-import "keyboard" ^
    --collect-all "openwakeword" ^
    --noconfirm ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo   PyInstaller build failed!
    pause
    exit /b 1
)
echo   PyInstaller build complete!
echo.

:: Step 3: Fix MSVCP140.dll issue
echo [3/5] Fixing Visual C++ Runtime and openwakeword resources...
if exist "C:\Windows\System32\MSVCP140.dll" (
    copy "C:\Windows\System32\MSVCP140.dll" "dist\WinVE\_internal\" > nul
    echo   MSVCP140.dll copied successfully!
) else (
    echo   Warning: MSVCP140.dll not found in System32
    echo   You may need to install Visual C++ Redistributable
)

:: Copy openwakeword resources manually
echo   Copying openwakeword resources...
if exist "%SITE_PACKAGES%\openwakeword\resources" (
    xcopy /E /I /Y "%SITE_PACKAGES%\openwakeword\resources" "dist\WinVE\_internal\openwakeword\resources\" > nul
    echo   openwakeword resources copied successfully!
) else (
    echo   Warning: openwakeword resources not found in %SITE_PACKAGES%
)
echo.

:: Step 4: Test the build
echo [4/5] Testing the build...
if exist "dist\WinVE\WinVE.exe" (
    echo   WinVE.exe created successfully!
    echo   Size: 
    for %%I in ("dist\WinVE\WinVE.exe") do echo     %%~zI bytes
) else (
    echo   WinVE.exe not found!
    pause
    exit /b 1
)
echo.

:: Step 5: Build installer with Inno Setup
echo [5/5] Building installer with Inno Setup...
set INNO_PATH="C:\Program Files (x86)\Inno Setup 6\Compil32.exe"
if not exist %INNO_PATH% (
    echo   Inno Setup not found at %INNO_PATH%
    echo   Please install Inno Setup 6 or update the path
    echo   Skipping installer build...
    goto :skip_installer
)

if not exist "setup.iss" (
    echo   setup.iss not found!
    echo   Please create the Inno Setup script first
    goto :skip_installer
)

echo   Building installer...
%INNO_PATH% /cc "setup.iss"
if %ERRORLEVEL% neq 0 (
    echo   Installer build failed!
    pause
    exit /b 1
)

if exist "inno\WinVE-Setup.exe" (
    echo   Installer created successfully!
    echo   Location: inno\WinVE-Setup.exe
    echo   Size: 
    for %%I in ("inno\WinVE-Setup.exe") do echo     %%~zI bytes
) else (
    echo   Installer not found!
)

:skip_installer
echo.
echo ========================================
echo            BUILD COMPLETE!
echo ========================================
echo.
echo Files created:
echo   dist\WinVE\WinVE.exe - Standalone application
if exist "inno\WinVE-Setup.exe" (
    echo   inno\WinVE-Setup.exe - Windows installer
)
echo.
echo Ready for distribution!
echo.
pause