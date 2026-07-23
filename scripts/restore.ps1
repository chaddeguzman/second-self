[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Archive,
    [Parameter(Mandatory = $true)]
    [string]$Destination
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command age -ErrorAction SilentlyContinue)) {
    throw "age is required. Install it with: winget install --id FiloSottile.age --exact"
}
$Archive = [IO.Path]::GetFullPath($Archive)
$Destination = [IO.Path]::GetFullPath($Destination)
$Checksum = "$Archive.sha256"
if (-not (Test-Path -LiteralPath $Archive) -or -not (Test-Path -LiteralPath $Checksum)) {
    throw "Archive and matching .sha256 file are required."
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

$TempTar = Join-Path ([IO.Path]::GetTempPath()) "$([IO.Path]::GetFileNameWithoutExtension($Archive)).tar"
try {
    age -d -o $TempTar $Archive
    if ($LASTEXITCODE -ne 0) { throw "age decryption failed." }
    tar -xf $TempTar -C $Destination
    if ($LASTEXITCODE -ne 0) { throw "tar restore failed." }
    Write-Host "Restore completed: $Destination"
}
finally {
    if (Test-Path -LiteralPath $TempTar) {
        Remove-Item -LiteralPath $TempTar -Force
    }
}

