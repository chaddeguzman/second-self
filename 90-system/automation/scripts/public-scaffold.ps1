function Get-PublicScaffoldManifest {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)

    $manifestPath = Join-Path $RepoRoot "90-system\app\second_self\public_scaffold.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Public scaffold manifest is missing: $manifestPath"
    }
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    if (
        $manifest.schema -ne "second-self-public-scaffold" -or
        $manifest.version -ne 1 -or
        -not $manifest.roots
    ) {
        throw "Public scaffold manifest is invalid."
    }
    return $manifest
}

function Connect-PublicScaffoldRoots {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$DataRoot
    )

    $manifest = Get-PublicScaffoldManifest -RepoRoot $RepoRoot
    $records = @()

    # Preflight every root before mutating any of them.
    foreach ($root in @($manifest.roots)) {
        $relativeRoot = [string]$root.path
        $source = Join-Path $RepoRoot $relativeRoot
        $target = Join-Path $DataRoot $relativeRoot
        $allowedFiles = @($root.files | ForEach-Object { [string]$_ })
        $existingJunction = $false

        if (Test-Path -LiteralPath $source) {
            $item = Get-Item -LiteralPath $source -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                $existingJunction = $true
            }
            elseif (-not $item.PSIsContainer) {
                throw "Refusing to replace non-directory scaffold root: $relativeRoot"
            }
            else {
                $sourcePrefix = $source + [IO.Path]::DirectorySeparatorChar
                $existingFiles = @(
                    Get-ChildItem -LiteralPath $source -File -Recurse -Force |
                        ForEach-Object {
                            $_.FullName.Substring($sourcePrefix.Length).Replace("\", "/")
                        }
                )
                $unexpectedFiles = @(
                    $existingFiles | Where-Object { $_ -notin $allowedFiles }
                )
                if ($unexpectedFiles.Count -ne 0) {
                    throw "Refusing to replace $relativeRoot scaffold containing unexpected files: $($unexpectedFiles -join ', ')"
                }
            }
        }

        $records += [PSCustomObject]@{
            Source = $source
            Target = $target
            Files = $allowedFiles
            ExistingJunction = $existingJunction
        }
    }

    foreach ($record in $records) {
        if ($record.ExistingJunction) {
            continue
        }
        New-Item -ItemType Directory -Force -Path $record.Target | Out-Null
        if (Test-Path -LiteralPath $record.Source) {
            foreach ($relative in $record.Files) {
                $sourceFile = Join-Path $record.Source $relative
                $targetFile = Join-Path $record.Target $relative
                if (
                    (Test-Path -LiteralPath $sourceFile -PathType Leaf) -and
                    -not (Test-Path -LiteralPath $targetFile)
                ) {
                    New-Item -ItemType Directory -Force -Path (Split-Path $targetFile) |
                        Out-Null
                    Copy-Item -LiteralPath $sourceFile -Destination $targetFile
                }
            }
            Remove-Item -LiteralPath $record.Source -Recurse -Force
        }
        New-Item -ItemType Junction -Path $record.Source -Target $record.Target |
            Out-Null
    }
}
