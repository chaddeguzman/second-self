[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$SecondSelfArguments
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
    $AppPath = Join-Path $RepoRoot "90-system\app"
    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$AppPath$([IO.Path]::PathSeparator)$env:PYTHONPATH"
    }
    else {
        $env:PYTHONPATH = $AppPath
    }
}

& $Python -m second_self @SecondSelfArguments
exit $LASTEXITCODE
