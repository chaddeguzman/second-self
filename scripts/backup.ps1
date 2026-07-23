[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Destination
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ConfigPath = Join-Path $RepoRoot ".main-brain.local.json"
if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Run scripts/bootstrap.ps1 first."
}
if (-not (Get-Command age -ErrorAction SilentlyContinue)) {
    throw "age is required. Install it with: winget install --id FiloSottile.age --exact"
}
if (-not (Get-Command tar -ErrorAction SilentlyContinue)) {
    throw "tar is required."
}

$Config = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
$DataRoot = [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($Config.data_root))
if (-not (Test-Path -LiteralPath $DataRoot)) {
    throw "Private data root does not exist: $DataRoot"
}
$Destination = [IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Force -Path $Destination | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Base = "main-brain-$Stamp"
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
    age -p -o $Archive $TempTar
    if ($LASTEXITCODE -ne 0) { throw "age encryption failed." }
    $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Archive).Hash.ToLowerInvariant()
    "$Hash  $([IO.Path]::GetFileName($Archive))" | Set-Content -Encoding ascii -LiteralPath $Checksum
    [ordered]@{
        format = 1
        created = (Get-Date).ToString("o")
        archive = [IO.Path]::GetFileName($Archive)
        sha256 = $Hash
        schema_version = (Get-Content -Raw -LiteralPath (Join-Path $DataRoot ".main-brain-schema")).Trim()
    } | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $Manifest
    Write-Host "Verified encrypted backup: $Archive"
}
finally {
    if (Test-Path -LiteralPath $TempTar) {
        Remove-Item -LiteralPath $TempTar -Force
    }
}

