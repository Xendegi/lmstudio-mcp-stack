<# .SYNOPSIS
  Launch all three MCP SSE servers in background windows.
.DESCRIPTION
  Starts lmstudio-manager (port 8765), comfyui-manager (port 8766),
  and vram-manager (port 8767) each in a new terminal window.
  Press Ctrl+C in any window to stop that server.
#>

$Root = Split-Path -Parent $PSCommandPath
$Python = "python"
if (Test-Path "$Root\.venv\Scripts\python.exe") {
    $Python = "$Root\.venv\Scripts\python.exe"
}

$Servers = @(
    @{Name="lmstudio-manager"; Script="lmstudio_manager_sse.py"; Port=8765},
    @{Name="comfyui-manager";  Script="comfyui_manager_sse.py";  Port=8766},
    @{Name="vram-manager";     Script="vram_manager_sse.py";     Port=8767}
)

Write-Host "Starting MCP SSE servers..." -ForegroundColor Cyan
Write-Host "Root: $Root" -ForegroundColor Gray
Write-Host "Python: $Python" -ForegroundColor Gray
Write-Host ""

foreach ($Srv in $Servers) {
    $ScriptPath = Join-Path $Root $Srv.Script
    if (-not (Test-Path $ScriptPath)) {
        Write-Warning "  $($Srv.Name) — script not found: $ScriptPath"
        continue
    }
    $Title = "$($Srv.Name) (:$(Srv.Port))"
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "& '$Python' '$ScriptPath'; pause" -WindowStyle Normal -WindowTitle $Title
    Write-Host "  [$($Srv.Name)] started on port $($Srv.Port)" -ForegroundColor Green
    Start-Sleep 1
}

Write-Host ""
Write-Host "All servers launched in separate windows." -ForegroundColor Cyan
Write-Host "Close each window to stop that server." -ForegroundColor Gray
