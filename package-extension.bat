@echo off
REM ============================================================================
REM GHL Sales Assistant — Chrome Extension Packaging Script (Windows)
REM Creates a distributable .zip from extension\ folder
REM Usage: package-extension.bat
REM ============================================================================
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "EXT_DIR=%SCRIPT_DIR%extension"
set "DIST_DIR=%SCRIPT_DIR%dist"
set "FOLDER_NAME=ghl-sales-assistant-extension"

REM --------------------------------------------------------------------------
REM 1. Read version from manifest.json via PowerShell
REM --------------------------------------------------------------------------
for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "(Get-Content '%EXT_DIR%\manifest.json' -Raw | ConvertFrom-Json).version"`) do set "VERSION=%%V"
if not defined VERSION set "VERSION=1.0.0"

set "ZIP_NAME=%FOLDER_NAME%-v%VERSION%.zip"

echo ============================================
echo   GHL Sales Assistant — Extension Packager
echo   Version: %VERSION%
echo ============================================
echo.

REM --------------------------------------------------------------------------
REM 2. Clean dist\ folder
REM --------------------------------------------------------------------------
if exist "%DIST_DIR%" (
    echo Cleaning existing dist\ folder...
    rmdir /s /q "%DIST_DIR%"
)
mkdir "%DIST_DIR%\%FOLDER_NAME%"

REM --------------------------------------------------------------------------
REM 3. Copy extension files using PowerShell (excludes unwanted files)
REM --------------------------------------------------------------------------
echo Copying extension files...

powershell -NoProfile -Command ^
    "$src = '%EXT_DIR%'; $dst = '%DIST_DIR%\%FOLDER_NAME%'; " ^
    "$excludeNames = @('.git', 'node_modules'); " ^
    "$excludeExts  = @('.md', '.svg'); " ^
    "$excludeFiles = @('.DS_Store', 'Thumbs.db'); " ^
    "Get-ChildItem -Path $src -Recurse -File | Where-Object { " ^
    "  $dominated = $false; " ^
    "  foreach ($ex in $excludeNames) { if ($_.FullName -match [regex]::Escape($ex)) { $dominated = $true } } " ^
    "  foreach ($ex in $excludeExts)  { if ($_.Extension -eq $ex) { $dominated = $true } } " ^
    "  foreach ($ex in $excludeFiles) { if ($_.Name -eq $ex) { $dominated = $true } } " ^
    "  -not $dominated " ^
    "} | ForEach-Object { " ^
    "  $rel = $_.FullName.Substring($src.Length); " ^
    "  $destPath = Join-Path $dst $rel; " ^
    "  $destDir  = Split-Path $destPath -Parent; " ^
    "  if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null } " ^
    "  Copy-Item $_.FullName -Destination $destPath " ^
    "}"

REM --------------------------------------------------------------------------
REM 4. Create .zip archive using PowerShell Compress-Archive
REM --------------------------------------------------------------------------
echo Creating %ZIP_NAME%...

powershell -NoProfile -Command ^
    "Compress-Archive -Path '%DIST_DIR%\%FOLDER_NAME%' -DestinationPath '%DIST_DIR%\%ZIP_NAME%' -Force"

REM --------------------------------------------------------------------------
REM 5. Show summary
REM --------------------------------------------------------------------------
echo.
echo Package created successfully!
echo ============================================

for %%F in ("%DIST_DIR%\%ZIP_NAME%") do set "FILE_SIZE=%%~zF"

REM Convert bytes to KB
set /a FILE_SIZE_KB=%FILE_SIZE% / 1024

REM Count files
set FILE_COUNT=0
for /f %%A in ('powershell -NoProfile -Command "(Get-ChildItem -Path '%DIST_DIR%\%FOLDER_NAME%' -Recurse -File).Count"') do set "FILE_COUNT=%%A"

echo   Output:  dist\%ZIP_NAME%
echo   Size:    %FILE_SIZE_KB% KB
echo   Files:   %FILE_COUNT%
echo ============================================
echo.
echo Contents:
powershell -NoProfile -Command ^
    "Get-ChildItem -Path '%DIST_DIR%\%FOLDER_NAME%' -Recurse -File | ForEach-Object { '  ' + $_.FullName.Substring('%DIST_DIR%\%FOLDER_NAME%\'.Length - 1) } | Sort-Object"
echo.
echo ============================================
echo   How to install in Chrome:
echo   1. Unzip dist\%ZIP_NAME%
echo   2. Open chrome://extensions
echo   3. Enable 'Developer mode' (top right)
echo   4. Click 'Load unpacked'
echo   5. Select the unzipped %FOLDER_NAME% folder
echo ============================================

endlocal
