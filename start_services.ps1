# HostForGuest local service startup script.
# For daily development, prefer: npm run dev

Write-Host "Starting HostForGuest local services..." -ForegroundColor Green
Write-Host ""

if (-not (Test-Path "package.json")) {
    Write-Host "Run this script from the repository root." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "node_modules")) {
    Write-Host "Warning: root node_modules not found. Run npm install first." -ForegroundColor Yellow
}

if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Warning: frontend node_modules not found. Run npm install --prefix frontend first." -ForegroundColor Yellow
}

Write-Host "Starting backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; npm run dev:api"

Start-Sleep -Seconds 3

Write-Host "Starting frontend on http://127.0.0.1:3055..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; npm run dev:frontend"

Write-Host ""
Write-Host "Services starting..." -ForegroundColor Green
Write-Host "Backend: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://127.0.0.1:3055" -ForegroundColor Cyan
Write-Host "API Docs: http://127.0.0.1:8000/api/v1/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Waiting 10 seconds for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "Testing connectivity..." -ForegroundColor Yellow

try {
    $backend = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "Backend is running." -ForegroundColor Green
} catch {
    Write-Host "Backend is not responding yet. Check the backend window for errors." -ForegroundColor Red
}

try {
    $frontend = Invoke-WebRequest -Uri "http://127.0.0.1:3055" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "Frontend is running." -ForegroundColor Green
} catch {
    Write-Host "Frontend is not responding yet. Check the frontend window for errors." -ForegroundColor Red
}

Write-Host ""
Write-Host "Done. Check the opened windows for any errors." -ForegroundColor Green
