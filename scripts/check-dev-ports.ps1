# Quick check: what is using dev ports 8000, 3055, 3060 (TouristGuideLocal local stack)
# Run from repo root:  powershell -ExecutionPolicy Bypass -File scripts/check-dev-ports.ps1

Write-Host "=== TCP listeners (8000, 8010, 3055, 3060) ===" -ForegroundColor Cyan
8000, 8010, 3055, 3060 | ForEach-Object {
    $p = $_
    $lines = netstat -ano | Select-String ":$p\s"
    if ($lines) {
        Write-Host "`nPort $p" -ForegroundColor Yellow
        $lines | ForEach-Object { Write-Host $_.Line }
    } else {
        Write-Host "Port $p : (no LISTENING match in netstat)" -ForegroundColor DarkGray
    }
}

Write-Host "`n=== Docker API/frontend (if compose is up) ===" -ForegroundColor Cyan
docker ps --format "table {{.Names}}\t{{.Ports}}" 2>$null | Select-String "tourist_guide|8000|3000|3001"

Write-Host "`nTip: free port 8000 — stop containerized api/frontend (if they were started with --profile docker-api):" -ForegroundColor Green
Write-Host "  npm run docker:stop-api"
