# LM Studio Workspace — MCP Server Stack

Three MCP (Model Context Protocol) servers that manage LM Studio, ComfyUI, and VRAM arbitration on a Windows host, accessible remotely via SSE.

## Servers

| Server | Port | Purpose |
|--------|------|---------|
| `lmstudio-manager` | 8765 | LM Studio model lifecycle, GPU info, benchmarking |
| `comfyui-manager` | 8766 | SD3.5 image generation via ComfyUI |
| `vram-manager` | 8767 | VRAM arbitration across the other two |

### lmstudio-manager

Manages [LM Studio](https://lmstudio.ai) — list, load, unload models, query GPU/CPU/RAM, benchmark models, profile memory usage.

### comfyui-manager

Generates images via [ComfyUI](https://github.com/comfyanonymous/ComfyUI) using SD3.5 Medium. Automatically manages VRAM before generation by checking with vram-manager and unloading LM Studio models if needed.

### vram-manager

Central VRAM authority. Queries nvidia-smi and LM Studio's API to coordinate 8 GB VRAM between LM Studio LLMs and ComfyUI image gen.

## Quick Start

```bash
# Install deps
pip install mcp httpx

# lmstudio-manager (stdio for local)
python lmstudio_manager.py

# Or all three as SSE servers (for remote Hermes access)
python lmstudio_manager_sse.py   # port 8765
python comfyui_manager_sse.py    # port 8766
python vram_manager_sse.py       # port 8767
```

## Hermes Integration

Add all three to `~/.hermes/config.yaml`:

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
