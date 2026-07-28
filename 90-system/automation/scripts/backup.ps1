[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Destination,
    [Parameter(Mandatory = $false)]
    [string]$SyncTo
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$ConfigPath = Join-Path $RepoRoot ".second-self.local.json"
if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Run 90-system/automation/scripts/bootstrap.ps1 first."
}

$Config = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
$DataRoot = [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($Config.data_root))
if (-not (Test-Path -LiteralPath $DataRoot)) {
    throw "Private data root does not exist: $DataRoot"
}

if ($SyncTo) {
    $Parent = [IO.Path]::GetFullPath($SyncTo)
    if (-not (Test-Path -LiteralPath $Parent)) {
        throw "Sync parent folder does not exist: $Parent"
    }
    $Target = Join-Path $Parent "second-self"
    New-Item -ItemType Directory -Force -Path $Target | Out-Null

    $Excludes = @(".git", ".second-self-cache", "node_modules", "__pycache__", ".pytest_cache", ".next", ".turbo", ".cache")
    $ExcludeFilter = $Excludes -join "|"

    $SourceItems = Get-ChildItem -LiteralPath $DataRoot -Force -File
    $SourceDirs = Get-ChildItem -LiteralPath $DataRoot -Force -Directory | Where-Object { $_.Name -notmatch "^($ExcludeFilter)$" }

    foreach ($file in $SourceItems) {
        $dest = Join-Path $Target $file.Name
        Copy-Item -LiteralPath $file.FullName -Destination $dest -Force
    }
    foreach ($dir in $SourceDirs) {
        $dest = Join-Path $Target $dir.Name
        if (Test-Path -LiteralPath $dest) {
            Remove-Item -LiteralPath $dest -Recurse -Force
        }
        Copy-Item -LiteralPath $dir.FullName -Destination $dest -Recurse -Force
    }

    $Existing = Get-ChildItem -LiteralPath $Parent -Directory -Filter "second-self-*" | Sort-Object LastWriteTime -Descending
    if ($Existing.Count -gt 5) {
        foreach ($old in $Existing | Select-Object -Skip 5) {
            Remove-Item -LiteralPath $old.FullName -Recurse -Force
        }
    }

    Write-Host "Obsidian-readable sync backup created: $Target"
    exit 0
}

$Age = Get-Command age -ErrorAction SilentlyContinue
if (-not $Age) {
    $Age = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages") -Filter "age.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
}
if (-not $Age) {
    throw "age is required. Install it with: winget install --id FiloSottile.age --exact"
}
$AgePath = if ($Age.Source) { $Age.Source } else { $Age.FullName }
if (-not (Get-Command tar -ErrorAction SilentlyContinue)) {
    throw "tar is required."
}

$Destination = [IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Force -Path $Destination | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Base = "second-self-$Stamp"
$TempTar = Join-Path ([IO.Path]::GetTempPath()) "$Base.tar"
$Archive = Join-Path $Destination "$Base.tar.age"
$Manifest = Join-Path $Destination "$Base.manifest.json"
$Checksum = "$Archive.sha256"
if (Test-Path -LiteralPath $Archive) {
    throw "Backup already exists: $Archive"
}

try {
    tar -cf $TempTar -C (Split-Path -Parent $DataRoot) (Split-Path -Leaf $DataRoot)
    if ($LASTEXITCODE -ne 0) { throw "tar failed." }
    & $AgePath -p -o $Archive $TempTar
    if ($LASTEXITCODE -ne 0) { throw "age encryption failed." }
    $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Archive).Hash.ToLowerInvariant()
    "$Hash  $([IO.Path]::GetFileName($Archive))" | Set-Content -Encoding ascii -LiteralPath $Checksum
    [ordered]@{
        format = 1
        created = (Get-Date).ToString("o")
        archive = [IO.Path]::GetFileName($Archive)
        sha256 = $Hash
        schema_version = (Get-Content -Raw -LiteralPath (Join-Path $DataRoot ".second-self-schema")).Trim()
    } | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $Manifest
    Write-Host "Verified encrypted backup: $Archive"
}
finally {
    if (Test-Path -LiteralPath $TempTar) {
        Remove-Item -LiteralPath $TempTar -Force
    }
}
