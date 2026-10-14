# clean_machine.ps1
# DESTRUCTIVE CLEANUP SCRIPT - FOR ACCEPTANCE TESTING ONLY
# Do NOT run this unless you explicitly intend to wipe all settings, models, logs, and installation files.

Write-Host "================================================="
Write-Host " AI SUITE - DESTRUCTIVE ACCEPTANCE TEST CLEANUP"
Write-Host "================================================="

# 1. Terminate all AI Suite processes
Write-Host "[1] Terminating AI Suite processes..."
Stop-Process -Name "AI Suite" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "AI-Suite-1.0.0-Setup" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 2. Uninstall AI Suite (Silent) if it exists
Write-Host "[2] Uninstalling AI Suite..."
$uninstallPath = "${env:ProgramFiles}\AI Suite\unins000.exe"
if (Test-Path $uninstallPath) {
    Write-Host "    Found uninstaller, running..."
    Start-Process -FilePath $uninstallPath -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -Wait -NoNewWindow
} else {
    Write-Host "    No uninstaller found at $uninstallPath"
}

# 3. Remove the old installation directory just in case
Write-Host "[3] Removing Program Files directory..."
$installDir = "${env:ProgramFiles}\AI Suite"
if (Test-Path $installDir) {
    Remove-Item -Path $installDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "    Removed $installDir"
}

# 4. Remove stale build/dist deployment artifacts
Write-Host "[4] Cleaning build/dist/installers..."
$repoDir = "d:\Coding\Jarvis"
$dirsToClean = @("build", "dist", "installers")
foreach ($dir in $dirsToClean) {
    $fullPath = Join-Path $repoDir $dir
    if (Test-Path $fullPath) {
        Remove-Item -Path $fullPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "    Removed $fullPath"
    }
}

# Remove any stray .exe or .msi in repo root
Get-ChildItem -Path $repoDir -Filter "*.exe" | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $repoDir -Filter "*.msi" | Remove-Item -Force -ErrorAction SilentlyContinue

# 5. Clean the entire %LOCALAPPDATA%\AISuite state
Write-Host "[5] Wiping %LOCALAPPDATA%\AISuite completely..."
$appDataDir = "${env:LOCALAPPDATA}\AISuite"
if (Test-Path $appDataDir) {
    Remove-Item -Path $appDataDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "    Removed $appDataDir"
}

Write-Host "================================================="
Write-Host " CLEANUP COMPLETE. MACHINE IS READY FOR FRESH TEST."
Write-Host "================================================="
