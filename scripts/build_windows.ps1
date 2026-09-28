$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv-build")) {
    py -3.12 -m venv .venv-build 2>$null
    if (-not (Test-Path ".venv-build")) { py -3.11 -m venv .venv-build }
}
& .\.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-build.txt

Remove-Item -Recurse -Force build, dist, release -ErrorAction SilentlyContinue
pyinstaller --noconfirm ScreenTranslator.spec

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($iscc) {
    & $iscc.Source installer\windows\ScreenTranslator.iss
    Write-Host "Installer created under release\\"
} else {
    Write-Host "Inno Setup not found. App folder created at dist\\ScreenTranslator"
    Write-Host "Install Inno Setup, then run: ISCC.exe installer\\windows\\ScreenTranslator.iss"
}
