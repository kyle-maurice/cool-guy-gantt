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
    --console `
    --collect-all fastapi `
    --collect-all starlette `
    --collect-all pydantic `
    --collect-all pydantic_core `
    --collect-all uvicorn `
    --collect-all jinja2 `
    --collect-all sqlalchemy `
    --collect-all anyio `
    --collect-all sniffio `
    --collect-all click `
    launcher.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nBuild succeeded: dist\CoolGuyGantt.exe" -ForegroundColor Green
} else {
    Write-Host "`nBuild failed (exit $LASTEXITCODE)." -ForegroundColor Red
    exit $LASTEXITCODE
}
