# PyInstaller build script for the Cool Guy Gantt launcher.
# Produces: dist\CoolGuyGantt.exe (single-file).

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

$py = ".\.venv\Scripts\python.exe"

Write-Host "Installing dependencies..." -ForegroundColor Cyan
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -r requirements.txt
& $py -m pip install --quiet pyinstaller

Write-Host "Cleaning previous builds..." -ForegroundColor Cyan
Remove-Item -Recurse -Force build, dist, CoolGuyGantt.spec -ErrorAction SilentlyContinue

Write-Host "Building executable..." -ForegroundColor Cyan
& $py -m PyInstaller `
    --name CoolGuyGantt `
    --onefile `
    --windowed `
    --add-data "app;app" `
    --add-data "static;static" `
    --add-data "templates;templates" `
    --hidden-import uvicorn.loops.auto `
    --hidden-import uvicorn.protocols.http.auto `
    --hidden-import uvicorn.protocols.websockets.auto `
    --hidden-import uvicorn.lifespan.on `
    --hidden-import uvicorn.lifespan.off `
    --hidden-import sqlalchemy.dialects.sqlite `
    launcher.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nBuild succeeded: dist\CoolGuyGantt.exe" -ForegroundColor Green
} else {
    Write-Host "`nBuild failed (exit $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}
