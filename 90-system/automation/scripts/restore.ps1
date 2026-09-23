[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Archive,
    [Parameter(Mandatory = $true)]
    [string]$Destination
)

$ErrorActionPreference = "Stop"
$Age = Get-Command age -ErrorAction SilentlyContinue
if (-not $Age) {
    $Age = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages") -Filter "age.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
}
if (-not $Age) {
    throw "age is required. Install it with: winget install --id FiloSottile.age --exact"
}
$AgePath = if ($Age.Source) { $Age.Source } else { $Age.FullName }
$Archive = [IO.Path]::GetFullPath($Archive)
$Destination = [IO.Path]::GetFullPath($Destination)
$Checksum = "$Archive.sha256"
$Manifest = $Archive -replace '\.tar\.age$', '.manifest.json'
if (-not (Test-Path -LiteralPath $Archive) -or -not (Test-Path -LiteralPath $Checksum) -or -not (Test-Path -LiteralPath $Manifest)) {
    throw "Archive, checksum, and matching manifest are required."
}
if (Test-Path -LiteralPath $Destination) {
    $existing = Get-ChildItem -Force -LiteralPath $Destination
    if ($existing.Count -gt 0) {
        throw "Restore destination must be empty: $Destination"
    }
}
else {
    New-Item -ItemType Directory -Path $Destination | Out-Null
}

$Expected = ((Get-Content -Raw -LiteralPath $Checksum).Split(" ")[0]).Trim().ToLowerInvariant()
$Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Archive).Hash.ToLowerInvariant()
if ($Expected -ne $Actual) {
    throw "Backup checksum verification failed."
}
$ManifestData = Get-Content -Raw -LiteralPath $Manifest | ConvertFrom-Json
if ($ManifestData.format -ne 1 -or $ManifestData.sha256 -ne $Actual -or $ManifestData.archive -ne [IO.Path]::GetFileName($Archive)) {
    throw "Backup manifest verification failed."
}

$TempTar = Join-Path ([IO.Path]::GetTempPath()) "$([IO.Path]::GetFileNameWithoutExtension($Archive)).tar"
$Staging = Join-Path ([IO.Path]::GetTempPath()) "second-self-restore-$([guid]::NewGuid().ToString('N'))"
$Policy = Join-Path $PSScriptRoot "backup_archive.py"
try {
    & $AgePath -d -o $TempTar $Archive
    if ($LASTEXITCODE -ne 0) { throw "age decryption failed." }
    python $Policy --validate $TempTar
    if ($LASTEXITCODE -ne 0) { throw "archive policy validation failed." }
    New-Item -ItemType Directory -Path $Staging | Out-Null
    tar -xf $TempTar -C $Staging
    if ($LASTEXITCODE -ne 0) { throw "tar restore failed." }
    $Roots = Get-ChildItem -LiteralPath $Staging -Force
    if ($Roots.Count -ne 1 -or -not $Roots[0].PSIsContainer) { throw "restore archive root is invalid." }
    Remove-Item -LiteralPath $Destination -Force
    Move-Item -LiteralPath $Roots[0].FullName -Destination $Destination -ErrorAction Stop
    Write-Host "Restore completed: $Destination"
}
finally {
    if (Test-Path -LiteralPath $TempTar) {
        Remove-Item -LiteralPath $TempTar -Force
    }
    if (Test-Path -LiteralPath $Staging) {
        Remove-Item -LiteralPath $Staging -Recurse -Force
    }
}

<#
.SYNOPSIS
Restore from a plain sync backup created with -SyncTo.
.DESCRIPTION
For plain sync backups, no decryption is needed. Copy the `second-self` folder
to the target machine and update `.second-self.local.json` to point `data_root`
to that location.
.EXAMPLE
 Copy-Item -Recurse -Force "D:\Backups\second-self" "%USERPROFILE%\SecondSelfData"
 Update-Content "%USERPROFILE%\SecondSelfData\.second-self.local.json" data_root
#>
