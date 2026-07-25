$LogFile = "G:\AI\ComfyUI\install.log"
$VenvPython = "G:\AI\ComfyUI\.venv\Scripts\python.exe"
$Pip = "G:\AI\ComfyUI\.venv\Scripts\pip.exe"
$ModelsDir = "G:\AI\ComfyUI\models\checkpoints"

function Log { param([string]$Msg) $ts = Get-Date -Format "HH:mm:ss"; "$ts $Msg" | Out-File -Append $LogFile; Write-Host "$ts $Msg" }

Log "=== Starting ComfyUI full install ==="

# 1. Install torch with CUDA
Log "Installing torch with CUDA 12.4..."
& $Pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 2>&1 | ForEach-Object { $_ | Out-File -Append $LogFile }
if ($LASTEXITCODE -eq 0) { Log "torch installed" } else { Log "torch install FAILED"; exit 1 }

# 2. Verify CUDA
Log "Verifying CUDA..."
$result = & $VenvPython -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0)}')" 2>&1
Log $result

# 3. Install ComfyUI requirements
Log "Installing ComfyUI requirements..."
& $Pip install -r G:\AI\ComfyUI\requirements.txt 2>&1 | ForEach-Object { $_ | Out-File -Append $LogFile }
if ($LASTEXITCODE -eq 0) { Log "ComfyUI requirements installed" } else { Log "requirements install FAILED"; exit 1 }

# 4. Create models directory
if (-not (Test-Path $ModelsDir)) { New-Item -ItemType Directory -Path $ModelsDir -Force | Out-Null }
Log "Models directory: $ModelsDir"

# 5. Download SD3.5 Medium model (7GB)
Log "Downloading SD3.5 Medium model (this may take a while)..."
$modelUrl = "https://huggingface.co/stabilityai/stable-diffusion-3.5-medium/resolve/main/sd3.5_medium.safetensors"
$modelPath = Join-Path $ModelsDir "sd3.5_medium.safetensors"
try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($modelUrl, $modelPath)
    Log "SD3.5 Medium downloaded: $modelPath"
} catch {
    Log "Direct download failed, trying with huggingface-hub..."
    & $Pip install huggingface-hub 2>&1 | Out-Null
    & $VenvPython -c "from huggingface_hub import hf_hub_download; hf_hub_download('stabilityai/stable-diffusion-3.5-medium', 'sd3.5_medium.safetensors', local_dir='$ModelsDir')" 2>&1 | ForEach-Object { $_ | Out-File -Append $LogFile }
    if ($LASTEXITCODE -eq 0) { Log "SD3.5 Medium downloaded via hub" } else { Log "SD3.5 download FAILED"; exit 1 }
}

# 6. Verify model file
$modelFile = Join-Path $ModelsDir "sd3.5_medium.safetensors"
if (Test-Path $modelFile) {
    $size = (Get-Item $modelFile).Length / 1GB
    Log "Model verified: $([math]::Round($size, 2)) GB"
} else {
    Log "Model file not found after download!"
    exit 1
}

Log "=== ComfyUI full install complete ==="
Log "To start: G:\AI\ComfyUI\.venv\Scripts\python.exe -m comfyui --listen 0.0.0.0"
