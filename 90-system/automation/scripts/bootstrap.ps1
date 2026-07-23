[CmdletBinding()]
param(
    [string]$DataRoot = (Join-Path $env:USERPROFILE "MainBrainData"),
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path

function Require-Or-OfferInstall {
    param([string]$Command, [string]$WingetId)
    if (Get-Command $Command -ErrorAction SilentlyContinue) {
        return
    }
    Write-Warning "$Command is not installed or not on PATH."
    Write-Host "Suggested command: winget install --id $WingetId --exact"
    if ($SkipDependencyInstall) {
        return
    }
    $answer = Read-Host "Run that installation command now? [y/N]"
    if ($answer -eq "y") {
        winget install --id $WingetId --exact
    }
}

Require-Or-OfferInstall -Command git -WingetId "Git.Git"
Require-Or-OfferInstall -Command python -WingetId "Python.Python.3.12"
$AgeInstalled = (Get-Command age -ErrorAction SilentlyContinue) -or
    (Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages") -Filter "age.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not $AgeInstalled) {
    Require-Or-OfferInstall -Command age -WingetId "FiloSottile.age"
}
$ObsidianPaths = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Obsidian\Obsidian.exe"),
    (Join-Path $env:LOCALAPPDATA "Obsidian\Obsidian.exe"),
    (Join-Path $env:ProgramFiles "Obsidian\Obsidian.exe")
)
$ObsidianDetected = (Get-Command obsidian -ErrorAction SilentlyContinue) -or
    ($ObsidianPaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1)
if (-not $ObsidianDetected) {
    Write-Warning "Obsidian was not detected."
    Write-Host "Suggested command: winget install --id Obsidian.Obsidian --exact"
    if (-not $SkipDependencyInstall) {
        $answer = Read-Host "Install Obsidian now? [y/N]"
        if ($answer -eq "y") {
            winget install --id Obsidian.Obsidian --exact
        }
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot ".venv"))) {
    python -m venv (Join-Path $RepoRoot ".venv")
}
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
& $Python -m pip install --disable-pip-version-check -r (Join-Path $RepoRoot "requirements.lock")
if ($LASTEXITCODE -eq 0) {
    & $Python -m pip install --disable-pip-version-check --no-deps -e $RepoRoot
}
if ($LASTEXITCODE -ne 0) {
    throw "Python dependency installation failed."
}

& $Python -m main_brain bootstrap --data-root $DataRoot
if ($LASTEXITCODE -ne 0) {
    throw "Private-data bootstrap failed."
}

$Links = @{
    (Join-Path $RepoRoot "01-strategy-storage") = (Join-Path $DataRoot "01-strategy-storage")
    (Join-Path $RepoRoot "02-skills-projects\projects") = (Join-Path $DataRoot "02-skills-projects\projects")
}
foreach ($entry in $Links.GetEnumerator()) {
    if (Test-Path -LiteralPath $entry.Key) {
        $item = Get-Item -LiteralPath $entry.Key -Force
        if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Refusing to replace non-link path: $($entry.Key)"
        }
        continue
    }
    New-Item -ItemType Junction -Path $entry.Key -Target $entry.Value | Out-Null
}

$encryptionVerified = $false
try {
    $systemDrive = Get-BitLockerVolume -MountPoint $env:SystemDrive -ErrorAction Stop
    $encryptionVerified = ($systemDrive.ProtectionStatus -eq "On")
}
catch {
    Write-Warning "Could not verify BitLocker/device encryption: $($_.Exception.Message)"
}
if (-not $encryptionVerified) {
    Write-Warning "Private data may not be protected by device encryption."
    $ack = Read-Host "Type ACKNOWLEDGE LOCAL DATA RISK to continue"
    if ($ack -ne "ACKNOWLEDGE LOCAL DATA RISK") {
        throw "Device-encryption risk was not acknowledged."
    }
}

git -C $RepoRoot config core.hooksPath 90-system/automation/git-hooks
Write-Host "Main Brain assembled at $RepoRoot"
Write-Host "Private data: $DataRoot"
Write-Host "Open $RepoRoot as the Obsidian vault."
