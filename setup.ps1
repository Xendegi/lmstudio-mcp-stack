<#
.SYNOPSIS
  One-command setup for the LM Studio MCP Stack.
.DESCRIPTION
  This script guides you through the full setup:
    1. Creates Python venv
    2. Installs dependencies (mcp, httpx, psutil)
    3. Prepares .env from template
    4. Verifies LM Studio API is reachable
    5. Provides instructions for ComfyUI setup
.NOTES
  Run this from the repository root:  .\setup.ps1
  Requires: Python 3.10+, Git, PowerShell 5.1+
  For ComfyUI setup, see README.md section "2. Install ComfyUI + SD3.5"
#>

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSCommandPath
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LM Studio MCP Stack — Setup"           -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check Python ────────────────────────
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    Write-Warning "Python not found. Install Python 3.10+ from https://python.org"
    exit 1
}
$ver = & python --version 2>&1
Write-Host "  Found: $ver at $py" -ForegroundColor Green

# ── Step 2: Create venv ─────────────────────────
Write-Host ""
Write-Host "[2/5] Creating Python virtual environment..." -ForegroundColor Yellow
$venvPath = "$Root\.venv"
if (Test-Path "$venvPath\Scripts\python.exe") {
    Write-Host "  venv already exists, skipping." -ForegroundColor Gray
} else {
    & python -m venv "$venvPath"
    Write-Host "  Created: $venvPath" -ForegroundColor Green
}
$venvPy = "$venvPath\Scripts\python.exe"
$venvPip = "$venvPath\Scripts\pip.exe"

# ── Step 3: Install deps ────────────────────────
Write-Host ""
Write-Host "[3/5] Installing Python dependencies..." -ForegroundColor Yellow
& $venvPip install --upgrade pip 2>&1 | Out-Null
& $venvPip install mcp httpx psutil 2>&1 | ForEach-Object {
    if ($_ -match "Successfully installed|Requirement already satisfied") {
        Write-Host "  $_" -ForegroundColor Green
    }
}
Write-Host "  Dependencies installed." -ForegroundColor Green

# ── Step 4: .env file ──────────────────────────
Write-Host ""
Write-Host "[4/5] Configuration..." -ForegroundColor Yellow
$envFile = "$Root\.env"
if (-not (Test-Path $envFile)) {
    if (Test-Path "$Root\.env.example") {
        Copy-Item "$Root\.env.example" $envFile
        Write-Host "  Created .env from .env.example" -ForegroundColor Green
        Write-Host "  >> Edit it now:  notepad $envFile" -ForegroundColor Gray
        Write-Host "  >> Set LM_STUDIO_API_KEY if you configured one in LM Studio." -ForegroundColor Gray
    }
} else {
    Write-Host "  .env already exists." -ForegroundColor Gray
}

# ── Step 5: Verify LM Studio ───────────────────
Write-Host ""
Write-Host "[5/5] Checking LM Studio API..." -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:1234/api/v1/models" -UseBasicParsing -TimeoutSec 5
    Write-Host "  LM Studio reachable! (HTTP $($r.StatusCode))" -ForegroundColor Green
} catch {
    Write-Warning "  LM Studio not reachable at http://127.0.0.1:1234"
    Write-Host "  Make sure LM Studio is running with HTTP API enabled:" -ForegroundColor Gray
    Write-Host "    Settings → Enable HTTP API (port 1234)" -ForegroundColor Gray
    Write-Host "  You can proceed anyway and configure later in .env" -ForegroundColor Gray
}

# ── Summary ────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!"                         -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Start servers:   .\start_servers.ps1"    -ForegroundColor White
Write-Host "  Or each manually:"                        -ForegroundColor Gray
Write-Host "    $venvPy $Root\lmstudio_manager_sse.py"  -ForegroundColor Gray
Write-Host "    $venvPy $Root\comfyui_manager_sse.py"   -ForegroundColor Gray
Write-Host "    $venvPy $Root\vram_manager_sse.py"      -ForegroundColor Gray
Write-Host ""
Write-Host "  Next steps (if not done already):"        -ForegroundColor Yellow
Write-Host "  1. Install ComfyUI (see README.md)"       -ForegroundColor White
Write-Host "  2. Download SD3.5 model files (see README.md)" -ForegroundColor White
Write-Host "  3. Start ComfyUI:  python C:\ComfyUI\main.py --listen 127.0.0.1 --port 8188" -ForegroundColor White
Write-Host "  4. Connect your MCP client (Hermes, etc.)" -ForegroundColor White
Write-Host ""
Write-Host "  Need help? Run:  Get-Content $Root\README.md -Tail 100" -ForegroundColor Gray
