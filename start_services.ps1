# TouristGuideLocal Service Startup Script
# This script starts both backend and frontend services

Write-Host "Starting TouristGuideLocal Services..." -ForegroundColor Green
Write-Host ""

# Check if venv exists
if (Test-Path "venv\Scripts\activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    . venv\Scripts\activate.ps1
} else {
    Write-Host "Warning: Virtual environment not found!" -ForegroundColor Red
}

# Start backend in new window
Write-Host "Starting backend on http://localhost:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; if (Test-Path venv\Scripts\activate.ps1) { . venv\Scripts\activate.ps1 }; python start.py"

Start-Sleep -Seconds 3

# Start frontend in new window
Write-Host "Starting frontend on http://localhost:3002..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev:3002"

Write-Host ""
Write-Host "Services starting..." -ForegroundColor Green
Write-Host "Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3002" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Waiting 10 seconds for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Test connectivity
Write-Host ""
Write-Host "Testing connectivity..." -ForegroundColor Yellow

try {
    $backend = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Backend is running!" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend not responding yet. Check the backend window for errors." -ForegroundColor Red
}

try {
    $frontend = Invoke-WebRequest -Uri "http://localhost:3002" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Frontend is running!" -ForegroundColor Green
} catch {
    Write-Host "❌ Frontend not responding yet. Check the frontend window for errors." -ForegroundColor Red
}

Write-Host ""
Write-Host "Done! Check the opened windows for any errors." -ForegroundColor Green











