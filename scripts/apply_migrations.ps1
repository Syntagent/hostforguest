<#
.SYNOPSIS
  Apply SQL files listed in migrations/MIGRATION_ORDER.txt to PostgreSQL.

.PARAMETER Host
  Postgres host (default: localhost).

.PARAMETER Port
  Postgres port (default: 5434 for local docker-compose postgres publish).

.PARAMETER Database
  Database name (default: tourist_guide_db).

.PARAMETER User
  Postgres user (default: tourist_guide_user).

.PARAMETER DryRun
  Print files only; do not execute psql.
#>
param(
    [string] $Host = "localhost",
    [int] $Port = 5434,
    [string] $Database = "tourist_guide_db",
    [string] $User = "tourist_guide_user",
    [switch] $DryRun
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent

$orderFile = Join-Path $repoRoot "migrations\MIGRATION_ORDER.txt"
$migrationsDir = Join-Path $repoRoot "migrations"

if (-not (Test-Path $orderFile)) {
    throw "Missing $orderFile"
}

$lines = Get-Content $orderFile | Where-Object { $_ -match '\S' -and $_ -notmatch '^\s*#' }
Write-Host "Applying $($lines.Count) migration(s) to ${User}@${Host}:${Port}/${Database}"

foreach ($line in $lines) {
    $rel = $line.Trim()
    $path = Join-Path $migrationsDir $rel
    if (-not (Test-Path $path)) {
        throw "Migration file not found: $path"
    }
    Write-Host "---- $rel ----"
    if ($DryRun) { continue }

    $env:PGPASSWORD = $env:POSTGRES_PASSWORD
    & psql -h $Host -p $Port -U $User -d $Database -v ON_ERROR_STOP=1 -f $path
    if ($LASTEXITCODE -ne 0) {
        throw "psql failed for $rel (exit $LASTEXITCODE)"
    }
}

Write-Host "Done."
