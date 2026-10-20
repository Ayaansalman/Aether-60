param(
    [switch]$Mock
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "aether-backend"
$FrontendDir = Join-Path $RootDir "aether-frontend"

# Read provider & model from environment or .env
$Provider = $env:MODEL_PROVIDER
$ModelName = $env:MODEL_NAME

if ($Mock) {
    $Provider = "mock"
    $ModelName = "mock-deterministic"
} else {
    $EnvFile = Join-Path $BackendDir ".env"
    if (Test-Path $EnvFile) {
        Get-Content $EnvFile | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith("#")) {
                if ($line -match "^MODEL_PROVIDER=(.*)$" -and -not $Provider) {
                    $Provider = $matches[1].Trim(' "''')
                }
                if ($line -match "^MODEL_NAME=(.*)$" -and -not $ModelName) {
                    $ModelName = $matches[1].Trim(' "''')
                }
            }
        }
    }
}

if (-not $Provider) { $Provider = "openai_compat" }
if (-not $ModelName) { $ModelName = "gemini-3.5-flash-lite" }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             AETHER GAME SYNTHESIS ENVIRONMENT             " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Active Provider : $Provider" -ForegroundColor Green
Write-Host "  Active Model ID : $ModelName" -ForegroundColor Green
Write-Host "  Backend Service : http://localhost:8000" -ForegroundColor Yellow
Write-Host "  Frontend Forge  : http://localhost:5173/forge" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Ensure Node.js is on PATH
if (-not (Get-Command "npm" -ErrorAction SilentlyContinue)) {
    if (Test-Path "C:\Program Files\nodejs") {
        $env:PATH = "C:\Program Files\nodejs;" + $env:PATH
    }
}

# Python executable
if ($env:AETHER_PYTHON -and (Test-Path $env:AETHER_PYTHON)) {
    $PythonExe = $env:AETHER_PYTHON
} elseif (Test-Path (Join-Path $BackendDir "venv\Scripts\python.exe")) {
    $PythonExe = Join-Path $BackendDir "venv\Scripts\python.exe"
} else {
    $PythonExe = "python"
}

# Start backend process directly
Write-Host "[1/3] Starting backend server on port 8000..." -ForegroundColor Gray
if ($Provider -eq "mock") {
    $env:MODEL_PROVIDER = "mock"
}
$BackendProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m","uvicorn","main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $BackendDir -PassThru -WindowStyle Hidden

# Start frontend in Vite dev server process directly
Write-Host "[2/3] Starting Vite dev server on port 5173..." -ForegroundColor Gray
$NpmCmd = if (Test-Path "C:\Program Files\nodejs\npm.cmd") { "C:\Program Files\nodejs\npm.cmd" } else { "npm.cmd" }
$FrontendProcess = Start-Process -FilePath $NpmCmd -ArgumentList "run","dev","--","--host","127.0.0.1","--port","5173" -WorkingDirectory $FrontendDir -PassThru -WindowStyle Hidden

# Wait for backend health
Write-Host "[3/3] Waiting for backend health check (http://127.0.0.1:8000/api/v1/health)..." -ForegroundColor Gray
$MaxRetries = 30
$Healthy = $false

for ($i = 1; $i -le $MaxRetries; $i++) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($res -and $res.status -eq "ok") {
            $Healthy = $true
            break
        }
    } catch {
        # Retry
    }
    Write-Host "  Waiting for backend... ($i/$MaxRetries)" -ForegroundColor DarkGray
}

if ($Healthy) {
    Write-Host "Backend is healthy!" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Backend health check timed out. Frontend will open in offline fallback mode." -ForegroundColor Yellow
}

# Open browser to Forge
$ForgeUrl = if ($Mock) { "http://127.0.0.1:5173/studio?mode=fixture" } else { "http://127.0.0.1:5173/studio" }
Write-Host "Opening browser to $ForgeUrl..." -ForegroundColor Green
Start-Process $ForgeUrl

Write-Host "AETHER is running. Run scripts\stop_all.ps1 to cleanly stop all servers." -ForegroundColor Cyan
