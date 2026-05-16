# Same list as GitHub Actions + ci-smoke-backend.sh (scripts/ci-smoke-backend.txt).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$env:DISABLE_RATE_LIMIT = "1"
$env:SKIP_SENTENCE_TRANSFORMERS = "1"
$env:TOURISTGUIDE_PYTEST = "1"
$paths = Get-Content (Join-Path $PSScriptRoot "ci-smoke-backend.txt") |
    Where-Object { $_ -and ($_ -notmatch '^\s*#') } |
    ForEach-Object { $_.Trim() }
if (-not $paths) { throw "No test paths in ci-smoke-backend.txt" }
python -m pytest $paths -q --tb=short
