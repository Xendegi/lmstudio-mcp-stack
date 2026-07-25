# LM Studio Workspace — Agent Instructions

## Execution Conventions

### Canonical patterns (use these always)
1. **Windows commands**: Write `.ps1` script → `pwsh -File path\to\script.ps1`
2. **Linux commands**: Write `.sh` script → `pwsh -File scripts\linux.ps1 path\to\script.sh`
3. **Simple Linux cmd**: `pwsh -File scripts\ssh.ps1 "command"`
4. **LM Studio API**: `pwsh -File scripts\api.ps1 GET /api/v1/...`
5. **Model mgmt**: `pwsh -File scripts\models.ps1 list|load|unload`
6. **Quick chat test**: `pwsh -File scripts\chat.ps1 -Model qwen/qwen3.5-9b -Prompt "hello"`

### Why
PowerShell 5.1 is the outer shell and mangles `$`, `"`, `{`, `}`, `` ` ``, `|`. Writing scripts to disk first bypasses all quoting issues entirely.

## Helper Scripts (`G:\AI\LM-Studio\scripts\`)
| Script | Purpose |
|--------|---------|
| `api.ps1` | LM Studio REST API `Method Path [Body]` |
| `models.ps1` | List/load/unload loaded models |
| `chat.ps1` | Quick chat with any loaded model |
| `ssh.ps1` | Single-shot SSH command to Linux |
| `linux.ps1` | Write+SCP+bash remote script execution |
| `ps7.ps1` | Execute PS7 code from string (base64-encoded) |
| `lmgr_sse.ps1` | Start/stop/restart/status SSE server for remote MCP access |

## MCP Servers (Windows)
| Server | Port | File | Purpose |
|--------|------|------|---------|
| `lmstudio-manager` | 8765 | `lmstudio_manager_sse.py` | LM Studio model mgmt, GPU info |
| `comfyui-manager` | 8766 | `comfyui_manager_sse.py` | SD3.5 image generation via ComfyUI |
| `vram-manager` | 8767 | `vram_manager_sse.py` | VRAM arbitration across servers |

### VRAM Auto-Management
- `comfyui-manager` calls `vram-manager` before every `generate_image`
- If LM Studio has a model loaded (using VRAM), it auto-unloads it before generation
- After generation, call `vram-manager restore_lm_studio_model` to reload Qwen
- Disable with env var `COMFYUI_AUTO_MANAGE_VRAM=0`
- Threshold: `COMFYUI_VRAM_REQUIRED_MB=8000` (default)

## Environment
- **Windows**: i7-9700K, 64GB, RTX 3070 Ti (8GB VRAM), `G:\AI\LM-Studio\`
- **Linux**: HP EliteBook, Ubuntu 26, `hpmaster@192.168.2.120:2222`, key `~/.ssh/id_ed25519`
- **APIs**: LM Studio at `192.168.2.100:1234`, key `sk-lm-rTgbTGyG:DGJ5nhlDtjok9UFuDtMx`
- **Proxy**: SOCKS `192.168.2.120:10808`, `no_proxy=192.168.2.100`
- **SSH**: `C:\Windows\System32\OpenSSH\ssh.exe`, `scp.exe`

## Models (8GB VRAM — one at a time)
- **Main**: `qwen/qwen3.5-9b` — ctx=65536, thinking=off, tokens=8192
- **Aux**: `qwen3-8b-32k` — ctx=32768, thinking=off, tokens=8192, only native context
- **Image**: `sd3.5_medium.safetensors` (4.8GB) + text encoders (6.2GB) via ComfyUI

## Constraints
- MCP watchdog auto-unloads non-main models every 30s
- Hermes source code — never modify, only config/skills/data
- Qwen3.5 reasoning: only `on`|`off` (no `medium`)
- 8GB VRAM shared across all loaded models and ComfyUI
- Cannot run LM Studio + ComfyUI concurrently — VRAM Manager handles this
- SD3.5 Medium uses ~8.8GB VRAM peak (fits via async offloading)

## Context Menu State
### File right-click — 5 submenus + 3 top-level
- **Open >** Notepad++, Mp3tag
- **Compress >** Add to archive (7-Zip), Extract here (7-Zip), Add to archive (WinRAR), Extract here (WinRAR)
- **Create >** Resize image (Image Resizer), Create PDF (PDFCreator)
- **Share >** Share, MEGA
- **Tools >** What is locking this? (LockHunter), Take Ownership, Compare files (MobaDiff), Remove properties, Encryption settings
- **Top-level:** Open With (built-in), Fences, FileConverter (has own submenu from shell extension)

### Folder right-click
- Submenus: Terminal, Development, Media, SystemTools
- Shellex: 7-Zip, FencesShellExt, PintoStartScreen, WinRAR
- Built-in: open, explore, opennewprocess, opennewtab, opennewwindow, pintohome, Search Everything

### Desktop/folder background
- Submenus: Terminal, Development
- No redundant cmd/PowerShell/WSL (removed)

### Image files (.jpg/.png/.bmp/.gif/.tiff/.webp/.ico/.heic/.heif)
- **Edit >** Paint, Paint 3D, PhotoPad
- **Convert >** Pixillion Image Converter
- **Set as desktop background** (top-level)
- **Print** (HEIC/HEIF only)

### Disabled handlers (file)
PicaView, HDCleaner, TweakPower, SDECon32/64, AccExt, CnvShell, BRUMenuHandler, WinRAR32, Taskband Pin, BdShlExt, Start Menu Pin, EncryptionMenu, ANotepad++64, Mp3tagShell, LockHunterShellExt, PDFCreator.ShellContextMenu, FileConverterExtension, Image Resizer, ModernSharing, 7-Zip, WinRAR, MEGA, Sharing, WorkFolders (protected, cannot delete)

### Disabled handlers (folder)
AccExt, HDCleaner, TweakPower, jetAudio, Library Location, Offline Files, WinRAR32, BdShlExt, Start Menu Pin

### Key registry knowledge
- PS5.1 `HKCR:` PSDrive is BROKEN — use `reg add` via batch files or `reg import` for .reg files
- `SubCommands` cascading menu BROKEN system-wide — must use `ExtendedSubCommandsKey`
- `*\shellex` path causes PowerShell to hang — use `reg.exe` via batch/cmd for those
- Windows uses `Folder\shell` for folder-item right-clicks, `Directory\Background\shell` for desktop/folder empty space
- `*Sub` keys (DevSub, TerminalSub etc.) contain submenu content — NEVER delete them
- cmd/Powershell/WSL in Background are Windows-protected (Access Denied on delete)
