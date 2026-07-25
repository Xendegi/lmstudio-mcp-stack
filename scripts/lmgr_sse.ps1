param(
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$VenvPython = Join-Path $RootDir ".venv" "Scripts" "python.exe"
$SseScript = Join-Path $RootDir "lmstudio_manager_sse.py"
$LogFile = Join-Path $RootDir "lmgr_sse.log"
$PidFile = Join-Path $RootDir "lmgr_sse.pid"
$Port = if ($env:LMGR_SSE_PORT) { $env:LMGR_SSE_PORT } else { 8765 }

function Get-RunningPid {
    if (Test-Path $PidFile) {
        $foundPid = Get-Content $PidFile -Raw | ForEach-Object { $_.Trim() }
        $proc = Get-Process -Id $foundPid -ErrorAction SilentlyContinue
        if ($proc) {
            $cmdline = Get-CimInstance Win32_Process -Filter "ProcessId=$foundPid" | Select-Object -ExpandProperty CommandLine
            if ($cmdline -like "*lmstudio_manager_sse.py*") {
                return $foundPid
            }
        }
    }
    return $null
}

function Get-PortProcess {
    $conn = netstat -ano | Select-String ":$Port\s" | Select-String "LISTENING"
    foreach ($line in $conn) {
        $parts = $line -split '\s+'
        $foundPid = $parts[-1]
        $cmdline = Get-CimInstance Win32_Process -Filter "ProcessId=$foundPid" | Select-Object -ExpandProperty CommandLine
        if ($cmdline -like "*python*") {
            return $foundPid
        }
    }
    return $null
}

switch ($Action) {
    "start" {
        $existing = Get-RunningPid
        if ($existing) {
            Write-Host "Already running (PID $existing). Use 'restart' or 'stop' first."
            exit 0
        }
        $existing = Get-PortProcess
        if ($existing) {
            Write-Host "Port $Port already in use by PID $existing."
            exit 1
        }
        Write-Host "Starting lmstudio-manager SSE on port $Port..."
        $proc = Start-Process -FilePath $VenvPython -ArgumentList "-u", $SseScript -PassThru -RedirectStandardOutput $LogFile -RedirectStandardError "${LogFile}.err"
        $proc.Id | Out-File -FilePath $PidFile -Encoding ascii
        Start-Sleep -Seconds 3
        $test = Get-RunningPid
        if ($test) {
            Write-Host "Started (PID $test). Log: $LogFile"
        } else {
            Write-Host "Failed to start. Check: $LogFile and ${LogFile}.err"
        }
    }
    "stop" {
        $foundPid = Get-RunningPid
        if (-not $foundPid) { $foundPid = Get-PortProcess }
        if ($foundPid) {
            Write-Host "Stopping PID $foundPid..."
            Stop-Process -Id $foundPid -Force -ErrorAction SilentlyContinue
            Remove-Item $PidFile -ErrorAction SilentlyContinue
            Write-Host "Stopped."
        } else {
            Write-Host "Not running."
        }
    }
    "restart" {
        & $MyInvocation.MyCommand.Path -Action stop
        Start-Sleep -Seconds 1
        & $MyInvocation.MyCommand.Path -Action start
    }
    "status" {
        $foundPid = Get-RunningPid
        if (-not $foundPid) { $foundPid = Get-PortProcess }
        if ($foundPid) {
            $proc = Get-Process -Id $foundPid
            Write-Host "Status: RUNNING (PID $foundPid, started $($proc.StartTime))"
        } else {
            Write-Host "Status: STOPPED"
        }
    }
}
