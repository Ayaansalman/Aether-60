# AETHER Standalone Real-Model Evaluation Runner (Phase 6 / Blueprint Section 15.2)
# Parameters: ModelId, Delay, MaxRequests, Mock switch
# Sets env vars for the process only (fallback disabled: MODEL_FALLBACKS="" and AETHER_ALLOW_FALLBACK=0)
# Starts Vite server, runs run_eval.py --real --qa-mode real, stops Vite server,
# copies artifacts to docs/eval/, and regenerates docs/EVAL_RESULTS.md from ALL artifacts in docs/eval/.

[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [Alias("Model")]
    [string]$ModelId = "gemini-3.5-flash-lite",

    [Parameter(Position=1)]
    [double]$Delay = 5.0,

    [Parameter(Position=2)]
    [int]$MaxRequests = 60,

    [Parameter(Position=3)]
    [Alias("Label")]
    [string]$RunLabel = "Run D: upgraded engine (GameIR with new enemy types, layouts and defeat_enemies); same 12 prompts as Run A, so engine and repair prompt differ from Run A",

    [switch]$Mock
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "aether-backend"
$FrontendDir = Join-Path $RootDir "aether-frontend"
$DocsEvalDir = Join-Path $RootDir "docs\eval"
$ArtifactsEvalDir = Join-Path $RootDir "artifacts\eval"

# 1. Enforce process-only environment
$env:MODEL_NAME = $ModelId
$env:MODEL_FALLBACKS = ""             # Fallback strictly disabled
$env:AETHER_ALLOW_FALLBACK = "0"
$env:BENCH_DELAY_SECONDS = "$Delay"
$env:BENCH_MAX_REQUESTS = "$MaxRequests"

if ($Mock) {
    $env:MODEL_PROVIDER = "mock"
    $Provider = "mock"
} else {
    $env:MODEL_PROVIDER = "openai_compat"
    $Provider = "openai_compat"
}

# Python executable
if ($env:AETHER_PYTHON -and (Test-Path $env:AETHER_PYTHON)) {
    $PythonExe = $env:AETHER_PYTHON
} elseif (Test-Path (Join-Path $BackendDir "venv\Scripts\python.exe")) {
    $PythonExe = Join-Path $BackendDir "venv\Scripts\python.exe"
} else {
    $PythonExe = "python"
}

# Ensure Node.js is on PATH
if (-not (Get-Command "npm" -ErrorAction SilentlyContinue)) {
    if (Test-Path "C:\Program Files\nodejs") {
        $env:PATH = "C:\Program Files\nodejs;" + $env:PATH
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             AETHER STANDALONE EVALUATION RUNNER            " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Active Provider : $Provider" -ForegroundColor Green
Write-Host "  Model ID        : $ModelId" -ForegroundColor Green
Write-Host "  Fallback Status : DISABLED (MODEL_FALLBACKS='', AETHER_ALLOW_FALLBACK=0)" -ForegroundColor Yellow
Write-Host "  Pacing Delay    : $Delay seconds" -ForegroundColor Gray
Write-Host "  Request Budget  : $MaxRequests requests" -ForegroundColor Gray
Write-Host "  QA Mode         : real (Headless Playwright Browser)" -ForegroundColor Gray
Write-Host "  Execution Mode  : $(if ($Mock) {'MOCK (Safe Dry Run, Zero Real API Calls)'} else {'REAL MODEL EVALUATION'})" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Helper to cleanly stop port 5173
function Stop-VitePort {
    try {
        $conns = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
        if ($conns) {
            $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($p in $pids) {
                if ($p -gt 4) {
                    Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
                }
            }
        }
    } catch {}
}

# Clean any existing Vite process on port 5173
Stop-VitePort

# 2. Start Vite dev server for real browser QA
Write-Host "[1/5] Starting Vite dev server on port 5173 for real browser QA..." -ForegroundColor Gray
$FrontendCommand = "`$env:PATH = 'C:\Program Files\nodejs;' + `$env:PATH; npx.cmd vite --host 127.0.0.1 --port 5173"
$ViteProc = Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "cd '$FrontendDir'; $FrontendCommand" -WindowStyle Minimized -PassThru

# Wait for Vite readiness
$ViteReady = $false
for ($i = 1; $i -le 25; $i++) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-WebRequest -Uri "http://127.0.0.1:5173/" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($res -and $res.StatusCode -eq 200) {
            $ViteReady = $true
            break
        }
    } catch {}
    Write-Host "  Waiting for Vite on port 5173... ($i/25)" -ForegroundColor DarkGray
}

if (-not $ViteReady) {
    Write-Host "[ERROR] Vite server failed to start within timeout. Aborting." -ForegroundColor Red
    Stop-VitePort
    exit 1
}
Write-Host "  [+] Vite server ready at http://127.0.0.1:5173/" -ForegroundColor Green

# 3. Run run_eval.py
Write-Host "[2/5] Running AETHER evaluation suite..." -ForegroundColor Gray
$EvalArgs = @("scripts/run_eval.py", "--qa-mode", "real", "--delay", "$Delay", "--max-requests", "$MaxRequests")
if (-not $Mock) {
    $EvalArgs += "--real"
}
if ($RunLabel) {
    $EvalArgs += @("--run-label", $RunLabel)
}

$ExitCode = 0
try {
    & $PythonExe @EvalArgs
    $ExitCode = $LASTEXITCODE
} catch {
    Write-Host "[ERROR] run_eval.py failed with exception: $_" -ForegroundColor Red
    $ExitCode = 1
}

# 4. Stop Vite server
Write-Host "[3/5] Stopping Vite dev server..." -ForegroundColor Gray
Stop-VitePort
if ($ViteProc -and -not $ViteProc.HasExited) {
    Stop-Process -Id $ViteProc.Id -Force -ErrorAction SilentlyContinue
}
Write-Host "  [+] Vite server stopped." -ForegroundColor Green

# 5. Copy artifacts to docs/eval/
Write-Host "[4/5] Copying evaluation artifacts to docs/eval/..." -ForegroundColor Gray
if (-not (Test-Path $DocsEvalDir)) {
    New-Item -ItemType Directory -Path $DocsEvalDir -Force | Out-Null
}

$CopiedCount = 0
if (Test-Path $ArtifactsEvalDir) {
    Get-ChildItem -Path $ArtifactsEvalDir -File | Where-Object { $_.Name -match "^eval_" } | ForEach-Object {
        $dest = Join-Path $DocsEvalDir $_.Name
        Copy-Item -Path $_.FullName -Destination $dest -Force
        $CopiedCount++
    }
}
Write-Host "  [+] Copied $CopiedCount artifact file(s) to docs/eval/" -ForegroundColor Green

# 6. Regenerate docs/EVAL_RESULTS.md from ALL artifacts in docs/eval/
Write-Host "[5/5] Regenerating docs/EVAL_RESULTS.md from ALL historical artifacts..." -ForegroundColor Gray
$AggregatorScript = Join-Path $RootDir "scripts\aggregate_eval_results.py"
& $PythonExe $AggregatorScript

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  EVALUATION FINISHED. RESULTS SAVED TO docs/EVAL_RESULTS.md" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

exit $ExitCode
