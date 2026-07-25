# LM Studio MCP Stack

Three MCP (Model Context Protocol) servers that turn a Windows PC into a remotely-accessible AI powerhouse — LLM inference via **LM Studio**, image generation via **ComfyUI + Stable Diffusion 3.5 Medium**, with automatic **VRAM arbitration** between them.

Designed for headless operation behind an AI agent (e.g. [Hermes](https://github.com/NousResearch/hermes), Cline, Claude Desktop, or any MCP client) over SSE transport.

> **8 GB VRAM? No problem.** The VRAM Manager automatically unloads LM Studio models before image generation and tells you how to restore them after.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Windows PC                             │
│                                                          │
│  ┌─────────────────┐    ┌─────────────────┐             │
│  │ lmstudio-mgr    │    │ comfyui-mgr     │             │
│  │ :8765           │    │ :8766           │             │
│  │                 │    │                 │             │
│  │ • list_models   │    │ • generate_image│             │
│  │ • load_model    │    │ • list_checkpts │             │
│  │ • unload_model  │    │ • get_queue     │             │
│  │ • gpu_info      │    │ • health_check  │             │
│  │ • chat          │    └───────┬─────────┘             │
│  │ • benchmarks    │            │                        │
│  └───────┬─────────┘            │                        │
│          │                      │                        │
│          └──────────┬───────────┘                        │
│                     │                                    │
│              ┌──────┴──────┐                             │
│              │  vram-mgr   │  ← arbitrates 8 GB VRAM    │
│              │  :8767      │                             │
│              │             │                             │
│              │ • status    │                             │
│              │ • ensure    │                             │
│              │ • unload    │                             │
│              │ • restore   │                             │
│              └─────────────┘                             │
└──────────────────────────────────────────────────────────┘
         │ SSE   │ SSE     │ SSE
         └───────┴─────────┴───────────────→ MCP Client (Hermes, etc.)
```

**What happens when you say "generate an image of a cat":**
1. Hermes calls `comfyui-manager.generate_image(prompt="a cat")`
2. `comfyui-manager` first calls `vram-manager` to check VRAM
3. If LM Studio has a model loaded (using ~4-5 GB VRAM), vram-manager auto-unloads it
4. ComfyUI loads SD3.5 and generates the image using the freed VRAM
5. After generation, call `vram-manager.restore_lm_studio_model()` to reload your LLM

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Install (5 minutes)](#quick-install-5-minutes)
- [Manual Setup](#manual-setup)
  - [1. Install LM Studio](#1-install-lm-studio)
  - [2. Install ComfyUI + SD3.5](#2-install-comfyui--sd35)
  - [3. Install the MCP Servers](#3-install-the-mcp-servers)
  - [4. Configure Environment](#4-configure-environment)
  - [5. Start the Servers](#5-start-the-servers)
- [Hermes / MCP Client Integration](#hermes--mcp-client-integration)
- [Configuration Reference](#configuration-reference)
- [MCP Tools Reference](#mcp-tools-reference)
- [VRAM Management Deep Dive](#vram-management-deep-dive)
- [Troubleshooting](#troubleshooting)
- [File Structure](#file-structure)

---

## Prerequisites

### Hardware
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | NVIDIA 6 GB VRAM | NVIDIA 8 GB VRAM (RTX 3070 Ti or better) |
| RAM | 32 GB | 64 GB |
| Storage | 30 GB free | 50 GB free (SSD/NVMe) |
| OS | Windows 10 | Windows 11 |

### Software
- **[LM Studio](https://lmstudio.ai)** — local LLM runtime (free)
- **[ComfyUI](https://github.com/comfyanonymous/ComfyUI)** — node-based image gen (free, open-source)
- **Python 3.10 – 3.12** — for both ComfyUI and MCP servers
- **[CUDA 12.4+](https://developer.nvidia.com/cuda-downloads)** — for GPU acceleration
- **Git** — for cloning repos
- **HuggingFace account** — for downloading the gated SD3.5 model

### Model Files (downloaded during setup)
| File | Size | Source |
|------|------|--------|
| `sd3.5_medium.safetensors` | 4.8 GB | stabilityai/stable-diffusion-3.5-medium (gated) |
| `clip_l.safetensors` | 235 MB | ^ same repo |
| `clip_g.safetensors` | 1.3 GB | ^ same repo |
| `t5xxl_fp8_e4m3fn.safetensors` | 4.6 GB | ^ same repo |
| LM Studio model (e.g. Qwen 3.5 9B) | ~6 GB | LM Studio model browser |

> **Total download: ~17 GB.** Off-peak hours recommended.

---

## Quick Install (5 minutes)

If you already have LM Studio and ComfyUI installed with Python:

```powershell
# 1. Clone this repo
git clone https://github.com/athenamiro/lmstudio-mcp-stack
cd lmstudio-mcp-stack

# 2. Run the auto-installer
.\setup.ps1

# 3. Edit configuration
notepad .env

# 4. Launch all servers
.\start_servers.ps1
```

---

## Manual Setup

### 1. Install LM Studio

1. Download from [lmstudio.ai](https://lmstudio.ai) and install
2. Open LM Studio → Settings → **Enable HTTP API** (port 1234)
3. Download a model: Search for `qwen/qwen3.5-9b` or your preferred model
4. Set an API key if desired (Settings → API Key)
5. Verify the API works:
   ```powershell
   curl http://127.0.0.1:1234/api/v1/models/
   ```

### 2. Install ComfyUI + SD3.5

#### 2a. Clone and set up ComfyUI

```powershell
# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI C:\ComfyUI
cd C:\ComfyUI

# Create Python environment
python -m venv .venv

# Install PyTorch with CUDA (critical: use the CUDA index!)
.venv\Scripts\pip install torch==2.5.1+cu124 torchvision==0.20.1+cu124 torchaudio==2.5.1+cu124 --index-url https://download.pytorch.org/whl/cu124

# Install other dependencies
.venv\Scripts\pip install -r requirements.txt
```

> **If pip replaces torch with a non-CUDA version**, re-run the torch install from the CUDA index above, then install `typing-extensions>=4.14.1` from PyPI to fix dependency conflicts.

#### 2b. Accept SD3.5 license (required)

SD3.5 Medium is a **gated model** on HuggingFace. You must accept the license before downloading:

1. Create a free account at [huggingface.co](https://huggingface.co/join)
2. Go to https://huggingface.co/stabilityai/stable-diffusion-3.5-medium
3. Click **"Agree and access repository"** to accept the Stability AI Community License
4. Generate a **User Access Token** at https://huggingface.co/settings/tokens

#### 2c. Download SD3.5 model files

```powershell
# Log in to HuggingFace
C:\ComfyUI\.venv\Scripts\python -m huggingface_hub login
# Paste your token when prompted

# Download model checkpoint (to models/checkpoints/)
C:\ComfyUI\.venv\Scripts\python -c "
from huggingface_hub import hf_hub_download
dest = r'C:\ComfyUI\models\checkpoints'
hf_hub_download('stabilityai/stable-diffusion-3.5-medium', 'sd3.5_medium.safetensors', local_dir=dest)
"

# Download text encoders (to models/text_encoders/)
C:\ComfyUI\.venv\Scripts\python -c "
from huggingface_hub import hf_hub_download
dest = r'C:\ComfyUI\models\text_encoders'
for f in ['clip_l.safetensors', 'clip_g.safetensors', 't5xxl_fp8_e4m3fn.safetensors']:
    hf_hub_download('stabilityai/stable-diffusion-3.5-medium', f'text_encoders/{f}', local_dir=dest)
"
```

#### 2d. Verify ComfyUI

```powershell
C:\ComfyUI\.venv\Scripts\python C:\ComfyUI\main.py --quick-test-for-ci
# Should exit with code 0 and no errors
```

### 3. Install the MCP Servers

```powershell
# Clone this repo
git clone https://github.com/athenamiro/lmstudio-mcp-stack
cd lmstudio-mcp-stack

# Create environment and install deps
python -m venv .venv
.venv\Scripts\pip install mcp httpx psutil

# Copy and edit config
copy .env.example .env
notepad .env
```

**Editing `.env`:**
- Set `LM_STUDIO_API_KEY` to your LM Studio API key (if you set one)
- Set `COMFYUI_HOST` and `COMFYUI_PORT` to match your ComfyUI setup
- Adjust `COMFYUI_VRAM_REQUIRED_MB` based on your GPU (default 8000 for 8 GB cards)
- Change SSE ports if there are conflicts

### 4. Start the servers

**Option A: All in one command**
```powershell
.\start_servers.ps1
```

**Option B: Each in its own terminal**
```powershell
# Terminal 1 — LM Studio Manager
python lmstudio_manager_sse.py

# Terminal 2 — ComfyUI Manager
python comfyui_manager_sse.py

# Terminal 3 — VRAM Manager
python vram_manager_sse.py
```

**Option C: Background processes (PowerShell)**
```powershell
$root = "C:\lmstudio-mcp-stack"
$py = "$root\.venv\Scripts\python.exe"
Start-Process -WindowStyle Hidden -FilePath $py -ArgumentList "$root\lmstudio_manager_sse.py"
Start-Process -WindowStyle Hidden -FilePath $py -ArgumentList "$root\comfyui_manager_sse.py"
Start-Process -WindowStyle Hidden -FilePath $py -ArgumentList "$root\vram_manager_sse.py"
```

**Option D: Windows Task Scheduler (auto-start on boot)**
Create three tasks that run at startup:
```powershell
Action: Start a program
Program: C:\lmstudio-mcp-stack\.venv\Scripts\python.exe
Arguments: C:\lmstudio-mcp-stack\lmstudio_manager_sse.py
```

#### Verify all servers are running

```powershell
curl http://127.0.0.1:8765/sse
curl http://127.0.0.1:8766/sse
curl http://127.0.0.1:8767/sse
```

Also test with a quick health check from the MCP tools directly:

```powershell
# Using the Hermes venv Python (where mcp is installed):
.\venv\Scripts\python -c "
from comfyui_manager import health_check, list_checkpoints
print(health_check())
print(list_checkpoints())
"
```

---

## Hermes / MCP Client Integration

### Hermes (recommended)

Add this to `~/.hermes/config.yaml` on your Linux machine:

```yaml
mcp_servers:
  lmstudio-manager:
    url: "http://192.168.2.100:8765/sse"
    transport: sse
  comfyui-manager:
    url: "http://192.168.2.100:8766/sse"
    transport: sse
  vram-manager:
    url: "http://192.168.2.100:8767/sse"
    transport: sse
```

Replace `192.168.2.100` with your Windows PC's IP address.

Then restart the Hermes gateway and test:

```bash
# Restart gateway
systemctl --user restart hermes-gateway

# Test — ask Hermes:
# "Run health_check from comfyui-manager"
# "What's the GPU status of the LM Studio machine?"
# "Generate an image of a cyberpunk cat with a glowing neon collar, 4 steps, 512x512"
```

### Any MCP Client

```yaml
# claude_desktop_config.json, Cline, etc.
{
  "mcpServers": {
    "lmstudio-manager": {
      "url": "http://192.168.2.100:8765/sse",
      "transport": "sse"
    },
    "comfyui-manager": {
      "url": "http://192.168.2.100:8766/sse",
      "transport": "sse"
    },
    "vram-manager": {
      "url": "http://192.168.2.100:8767/sse",
      "transport": "sse"
    }
  }
}
```

> **Note:** MCP SSE transport requires the client to support `transport: sse`. Not all clients do — check your client's documentation. Hermes and custom FastMCP clients support it natively.

---

## Configuration Reference

All settings via environment variables. Create a `.env` file in the project root:

| Variable | Default | Description |
|----------|---------|-------------|
| **LM Studio** | | |
| `LM_STUDIO_BASE` | `http://127.0.0.1:1234` | LM Studio HTTP API URL |
| `LM_STUDIO_API_KEY` | — | API key if LM Studio requires one |
| **ComfyUI** | | |
| `COMFYUI_HOST` | `127.0.0.1` | ComfyUI server host |
| `COMFYUI_PORT` | `8188` | ComfyUI server port |
| **VRAM Management** | | |
| `COMFYUI_AUTO_MANAGE_VRAM` | `1` | Set to `0` to disable automatic VRAM management |
| `COMFYUI_VRAM_REQUIRED_MB` | `8000` | MB of VRAM to reserve before image generation |
| **SSE Server Ports** | | |
| `LMGR_SSE_HOST` | `0.0.0.0` | lmstudio-manager bind address |
| `LMGR_SSE_PORT` | `8765` | lmstudio-manager port |
| `COMFYUI_SSE_HOST` | `0.0.0.0` | comfyui-manager bind address |
| `COMFYUI_SSE_PORT` | `8766` | comfyui-manager port |
| `VRAM_SSE_HOST` | `0.0.0.0` | vram-manager bind address |
| `VRAM_SSE_PORT` | `8767` | vram-manager port |

---

## MCP Tools Reference

### lmstudio-manager (port 8765)

| Tool | Description | Parameters |
|------|-------------|------------|
| `health_check` | System health overview | — |
| `gpu_info` | Detailed GPU specs per adapter | — |
| `list_models` | All models available in LM Studio | — |
| `load_model` | Load a model | `model_name` |
| `unload_model` | Unload current model | `model_name` (optional) |
| `chat` | Quick prompt to loaded model | `prompt`, `model_name`, `system_prompt`, `temperature`, `max_tokens` |
| `benchmark_model` | Score model on task type | `task_type`, `model_name` |
| `compare_models` | Side-by-side benchmark | `model_names[]`, `task_type` |
| `resource_profile_model` | RAM/VRAM footprint | `model_name` |
| `best_model_for_task` | Quick recommendation | `category` |
| `self_check` | Verify connectivity & config | — |
| `context_stress_test` | Test context length behavior | `model_name` |
| `structured_output_test` | Test JSON output quality | `model_name` |
| `agent_compatibility_test` | Agent workflow suitability | `model_name` |

### comfyui-manager (port 8766)

| Tool | Description | Parameters |
|------|-------------|------------|
| `health_check` | ComfyUI reachability | — |
| `list_checkpoints` | Available SD models | — |
| `generate_image` | Generate image from prompt | `prompt`, `negative_prompt`, `model`, `steps`, `width`, `height`, `cfg`, `seed`, `wait_timeout` |
| `get_queue` | Current execution queue | — |

**Default `generate_image` parameters:**
- `steps`: 20 (good quality; 4 for quick tests)
- `width`/`height`: 1024 (SD3.5 native; 512 for faster results)
- `cfg`: 4.5 (SD3.5 recommended range: 3.5–6.0)
- `seed`: -1 (random)
- Model: auto-detects `sd3.5_medium.safetensors`

### vram-manager (port 8767)

| Tool | Description | Parameters |
|------|-------------|------------|
| `status_vram` | GPU VRAM usage + LM Studio loaded models | — |
| `ensure_vram` | Unload LM Studio if VRAM insufficient | `required_mb`, `wait_seconds` |
| `unload_lm_studio_model` | Unload specific (or all) LM Studio models | `model_key` |
| `restore_lm_studio_model` | Reload the last unloaded model | — |
| `list_loaded` | What LM Studio models are currently loaded | — |

---

## VRAM Management Deep Dive

### The Problem

With 8 GB VRAM:
- LM Studio (Qwen 3.5 9B Q4_K_M) uses **~4–5 GB VRAM**
- ComfyUI (SD3.5 Medium) uses **~8.8 GB VRAM peak** (with async offloading)

They **cannot run simultaneously**. Without VRAM management, `generate_image` would crash with an out-of-memory error.

### The Solution: Three-Phase Arbitration

```
Phase 1: CHECK
  vram-manager queries nvidia-smi for free VRAM
  → If >= 8000 MB free → proceed (skip)

Phase 2: UNLOAD (if needed)
  vram-manager queries LM Studio API for loaded models
  → If model found → POST /api/v1/models/unload
  → Poll nvidia-smi every 2s until VRAM is free (or timeout)

Phase 3: PROCEED
  → comfyui-manager queues the SD3.5 generation
  → ComfyUI's async offloading manages the 8.8 GB peak within 8 GB
  → After generation, call restore_lm_studio_model to reload the LLM
```

### Async Offloading (ComfyUI)

ComfyUI uses **asynchronous weight offloading** (enabled by default on NVIDIA GPUs). This means:
- Model weights are streamed from system RAM to VRAM as needed
- Not all weights are in VRAM at the same time
- Peak VRAM usage is ~1–2 GB lower than the model size
- This is what makes SD3.5 Medium (4.8 GB) + T5-XXL (4.6 GB) fit in 8 GB

### Manual VRAM Control

If auto-management is disabled (`COMFYUI_AUTO_MANAGE_VRAM=0`), manage VRAM yourself:

```python
# From your MCP client or agent:

# Before generation — free VRAM
await call("vram-manager", "ensure_vram", {"required_mb": 8000})

# Generate image
await call("comfyui-manager", "generate_image", {"prompt": "..."})

# After generation — restore LLM
await call("vram-manager", "restore_lm_studio_model")
```

---

## Troubleshooting

### "clip input is invalid: None" / "checkpoint does not contain a valid clip"

SD3.5 Medium stores text encoders in **separate files**, not inside the checkpoint. The `CheckpointLoaderSimple` node can't find them.

**Fix:** The workflow in `comfyui_manager.py` already uses `TripleCLIPLoader` + `CLIPTextEncodeSD3` instead. Ensure text encoder files are in `models/text_encoders/`:
```
models/text_encoders/clip_l.safetensors
models/text_encoders/clip_g.safetensors
models/text_encoders/t5xxl_fp8_e4m3fn.safetensors
```

### "HTTP 400: value_not_in_list" on TripleCLIPLoader

The text encoder filenames don't match what ComfyUI finds.

**Fix:** Check the actual filenames in `models/text_encoders/` and make sure they match the `clip_name1/2/3` parameters in `_build_txt2img_workflow()`.

### generate_image returns "VRAM check failed"

ComfyUI is not running, or VRAM can't be freed.

**Fix:**
1. Start ComfyUI: `python C:\ComfyUI\main.py --listen 127.0.0.1 --port 8188`
2. Check if another GPU app is using VRAM (game, renderer, etc.)
3. If LM Studio has a model loaded that won't unload, unload it manually:
   ```powershell
   curl -X POST http://127.0.0.1:1234/api/v1/models/unload -H "Content-Type: application/json" -d "{\"instance_id\":\"...\"}"
   ```

### "No module named 'mcp'"

The MCP SDK is required but not installed in the Python environment running the server.

**Fix:** `pip install mcp`

### torch version too old / DynamicVRAM requires torch 2.8+

This is a warning, not an error. SD3.5 works fine with torch 2.5.1+cu124. DynamicVRAM is a newer optimization that's nice-to-have, not required.

### ComfyUI API endpoints returning 404

Since ComfyUI 0.28.0, API endpoints changed:
- `/api/checkpoints` → `/object_info/CheckpointLoaderSimple`
- `/api/queue` → `/queue`
- `/api/history/{id}` → `/history/{id}`

These are already updated in `comfyui_manager.py`.

### Port already in use

Change the port in `.env`:
```ini
LMGR_SSE_PORT=8765
COMFYUI_SSE_PORT=8766
VRAM_SSE_PORT=8767
```

Or kill the existing process:
```powershell
netstat -ano | findstr :8765
taskkill /PID <PID> /F
```

---

## File Structure

```
lmstudio-mcp-stack/
│
├── lmstudio_manager.py          # LM Studio MCP server (all tools)
├── lmstudio_manager_sse.py      # SSE launcher for port 8765
│
├── comfyui_manager.py           # ComfyUI MCP server + VRAM auto-mgmt
├── comfyui_manager_sse.py       # SSE launcher for port 8766
│
├── vram_manager_core.py         # VRAM arbitration core logic
├── vram_manager.py              # VRAM MCP FastMCP wrapper
├── vram_manager_sse.py          # SSE launcher for port 8767
│
├── scripts/
│   ├── api.ps1                  # Raw LM Studio HTTP API caller
│   ├── models.ps1               # Model list/load/unload CLI
│   ├── chat.ps1                 # Quick chat with any loaded model
│   ├── ssh.ps1                  # SSH command to Linux host
│   ├── linux.ps1                # Write + SCP + execute remote script
│   ├── ps7.ps1                  # Execute PowerShell 7 code
│   ├── lmgr_sse.ps1             # lmstudio-manager lifecycle (start/stop/restart)
│   └── install_comfyui_full.ps1 # Full ComfyUI + SD3.5 auto-installer
│
├── start_servers.ps1            # Launch all 3 SSE servers in new windows
├── setup.ps1                    # One-command installer
├── .env.example                 # Configuration template
├── AGENTS.md                    # Workspace conventions
├── pyproject.toml               # Python project metadata
├── LICENSE                      # MIT
├── .gitignore
└── README.md
```

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

- [LM Studio](https://lmstudio.ai) — local LLM runtime
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — node-based image generation
- [Stability AI](https://stability.ai) — Stable Diffusion 3.5 Medium
- [Model Context Protocol](https://modelcontextprotocol.io) — MCP specification
- [Hermes](https://github.com/NousResearch/hermes) — AI agent framework
