# Start and Monitor Script for AIBI Project
# PowerShell Script to run main.py and monitor output in real-time

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "AIBI PROJECT - START AND MONITOR" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting Python main.py..." -ForegroundColor Yellow
Write-Host ""

# Start the process with output redirection
$process = Start-Process python -ArgumentList "main.py" -WindowStyle Normal -PassThru -NoNewWindow

Write-Host "[OK] Process started with PID: $($process.Id)" -ForegroundColor Green
Write-Host ""
Write-Host "========== MONITORING CONSOLE OUTPUT ==========" -ForegroundColor Cyan
Write-Host ""

# Wait a bit for output to start
Start-Sleep -Seconds 2

# Keep the process running
$process.WaitForExit()

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Yellow
Write-Host "Process exited with code: $($process.ExitCode)" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Yellow
