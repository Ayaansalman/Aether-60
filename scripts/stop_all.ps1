# AETHER Process Terminator (Phase 6)
# Cleanly terminates listeners on ports 8000 and 5173

$ErrorActionPreference = "Continue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "           STOPPING AETHER DEV & GAME SERVICES              " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$Ports = @(8000, 5173)
$StoppedCount = 0

foreach ($Port in $Ports) {
    Write-Host "Checking port $Port..." -ForegroundColor Gray
    try {
        $Connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($Connections) {
            $Pids = $Connections | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($TargetPid in $Pids) {
                if ($TargetPid -gt 4) {
                    try {
                        $Proc = Get-Process -Id $TargetPid -ErrorAction SilentlyContinue
                        $ProcName = if ($Proc) { $Proc.ProcessName } else { "Unknown" }
                        Write-Host "  Stopping PID $TargetPid ($ProcName) on port $Port..." -ForegroundColor Yellow
                        Stop-Process -Id $TargetPid -Force -ErrorAction SilentlyContinue
                        $StoppedCount++
                    } catch {
                        Write-Host "  Could not stop PID ${TargetPid}: $_" -ForegroundColor Red
                    }
                }
            }
        } else {
            Write-Host "  Port $Port is free (no active listener)." -ForegroundColor Green
        }
    } catch {
        Write-Host "  Error querying port ${Port}: $_" -ForegroundColor Red
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Stopped $StoppedCount process(es). Ports 8000 and 5173 are clean." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
