from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

for _var in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
    os.environ.pop(_var, None)

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("comfyui-manager")

BASE_DIR = Path(__file__).parent.resolve()
COMFYUI_DIR = BASE_DIR / "ComfyUI"
COMFYUI_PORT = int(os.environ.get("COMFYUI_PORT", "8188"))
COMFYUI_HOST = os.environ.get("COMFYUI_HOST", "127.0.0.1")
COMFYUI_BASE = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"

CLIENT = httpx.Client(timeout=httpx.Timeout(300.0, connect=5.0))

# VRAM auto-management
AUTO_MANAGE_VRAM = os.environ.get("COMFYUI_AUTO_MANAGE_VRAM", "1") == "1"
VRAM_REQUIRED_MB = int(os.environ.get("COMFYUI_VRAM_REQUIRED_MB", "8000"))

if AUTO_MANAGE_VRAM:
    try:
        from vram_manager_core import ensure_free_vram
    except ImportError:
        ensure_free_vram = None  # type: ignore[assignment]
else:
    ensure_free_vram = None


def _comfy_reachable() -> bool:
    try:
        r = CLIENT.get(f"{COMFYUI_BASE}/queue", timeout=3)
        return r.status_code < 500
    except Exception:
        return False


def _list_checkpoints_internal() -> list[str]:
    try:
        r = CLIENT.get(f"{COMFYUI_BASE}/object_info/CheckpointLoaderSimple", timeout=5)
        if r.status_code == 200:
            data = r.json()
            ckpt = data.get("CheckpointLoaderSimple", {})
            inp = ckpt.get("input", {})
            req = inp.get("required", {})
            names = req.get("ckpt_name", [[]])
            if names and isinstance(names[0], list):
                return names[0]
        return []
    except Exception:
        return []


def _queue_prompt(workflow: dict) -> dict[str, Any]:
    r = CLIENT.post(f"{COMFYUI_BASE}/prompt", json={"prompt": workflow}, timeout=10)
    if r.status_code != 200:
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    return {"ok": True, "response": r.json()}


def _queue_status() -> dict[str, Any]:
    try:
        r = CLIENT.get(f"{COMFYUI_BASE}/queue", timeout=3)
        if r.status_code == 200:
            return r.json()
        return {}
    except Exception:
        return {}


def _build_txt2img_workflow(
    prompt: str,
    negative_prompt: str = "",
    model: str = "",
    steps: int = 20,
    width: int = 1024,
    height: int = 1024,
    cfg: float = 4.5,
    seed: int = -1,
) -> dict:
    if seed < 0:
        seed = int(time.time() * 1000) % (2 ** 32)
    nodes = {}

    # Model checkpoint (provides MODEL and VAE)
    ckpt = model if model else "sd3.5_medium.safetensors"
    nodes["3"] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": ckpt},
    }

    # Triple CLIP loader for SD3 text encoders
    nodes["11"] = {
        "class_type": "TripleCLIPLoader",
        "inputs": {
            "clip_name1": "clip_l.safetensors",
            "clip_name2": "clip_g.safetensors",
            "clip_name3": "t5xxl_fp8_e4m3fn.safetensors",
        },
    }

    # CLIP text encode (positive) - SD3 style
    nodes["6"] = {
        "class_type": "CLIPTextEncodeSD3",
        "inputs": {
            "clip": ["11", 0],
            "clip_l": prompt,
            "clip_g": prompt,
            "t5xxl": prompt,
            "empty_padding": "none",
        },
    }

    # CLIP text encode (negative) - SD3 style
    nodes["7"] = {
        "class_type": "CLIPTextEncodeSD3",
        "inputs": {
            "clip": ["11", 0],
            "clip_l": negative_prompt,
            "clip_g": negative_prompt,
            "t5xxl": negative_prompt,
            "empty_padding": "none",
        },
    }

    # Empty SD3 latent image
    nodes["5"] = {
        "class_type": "EmptySD3LatentImage",
        "inputs": {"width": width, "height": height, "batch_size": 1},
    }

    # KSampler
    nodes["10"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["3", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0],
        },
    }

    # VAE decode
    nodes["8"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["10", 0], "vae": ["3", 2]},
    }

    # Save image
    nodes["9"] = {
        "class_type": "SaveImage",
        "inputs": {"images": ["8", 0], "filename_prefix": "comfyui_mcp"},
    }

    return nodes


def _get_history(prompt_id: str) -> dict[str, Any] | None:
    try:
        r = CLIENT.get(f"{COMFYUI_BASE}/history/{prompt_id}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if prompt_id in data:
                return data[prompt_id]
        return None
    except Exception:
        return None


def _wait_for_completion(prompt_id: str, timeout: int = 300) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        history = _get_history(prompt_id)
        if history:
            outputs = history.get("outputs", {})
            images = []
            for node_id, node_out in outputs.items():
                for key, val in node_out.items():
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict) and "filename" in item:
                                images.append(item)
            return {"ok": True, "status": "completed", "images": images, "history": history}
        # Check queue status
        try:
            q = _queue_status()
            if isinstance(q, dict) and not q.get("queue_running") and not q.get("queue_pending"):
                return {"ok": False, "status": "not_found", "error": "Prompt not found in history or queue"}
        except Exception:
            pass
        time.sleep(2)
    return {"ok": False, "status": "timeout", "error": f"Timed out after {timeout}s"}


@mcp.tool()
def health_check() -> dict[str, Any]:
    reachable = _comfy_reachable()
    return {
        "ok": True,
        "comfyui_reachable": reachable,
        "comfyui_url": COMFYUI_BASE,
        "comfyui_dir": str(COMFYUI_DIR),
    }


@mcp.tool()
def list_checkpoints() -> dict[str, Any]:
    models = _list_checkpoints_internal()
    return {"ok": True, "checkpoints": models, "count": len(models)}


@mcp.tool()
def generate_image(
    prompt: str,
    negative_prompt: str = "",
    model: str = "",
    steps: int = 20,
    width: int = 1024,
    height: int = 1024,
    cfg: float = 4.5,
    seed: int = -1,
    wait_timeout: int = 300,
) -> dict[str, Any]:
    if not _comfy_reachable():
        return {"ok": False, "error": "ComfyUI is not reachable. Start ComfyUI first."}
    vram_result = None
    if ensure_free_vram is not None:
        vram_result = ensure_free_vram(required_mb=VRAM_REQUIRED_MB, wait_seconds=60)
        if not vram_result.get("ok"):
            return {"ok": False, "error": f"VRAM check failed: {vram_result.get('error', 'unknown')}",
                    "vram": vram_result}
    workflow = _build_txt2img_workflow(
        prompt=prompt,
        negative_prompt=negative_prompt,
        model=model,
        steps=steps,
        width=width,
        height=height,
        cfg=cfg,
        seed=seed,
    )
    result = _queue_prompt(workflow)
    if not result.get("ok"):
        return result
    prompt_id = result["response"].get("prompt_id")
    if not prompt_id:
        resp = {"ok": False, "error": "No prompt_id in response"}
        if vram_result:
            resp["vram"] = vram_result
        return resp
    result = _wait_for_completion(prompt_id, timeout=wait_timeout)
    if vram_result:
        result["vram"] = vram_result
    return result


@mcp.tool()
def get_queue() -> dict[str, Any]:
    try:
        r = CLIENT.get(f"{COMFYUI_BASE}/queue", timeout=5)
        if r.status_code == 200:
            return {"ok": True, "queue": r.json()}
        return {"ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def get_system_info() -> dict[str, Any]:
    return {
        "ok": True,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "comfyui_dir": str(COMFYUI_DIR),
        "comfyui_exists": COMFYUI_DIR.exists(),
    }


def main() -> None:
    print(f"[comfyui-manager] Target: {COMFYUI_BASE}")
    print(f"[comfyui-manager] ComfyUI dir: {COMFYUI_DIR}")
    mcp.run()


if __name__ == "__main__":
    main()
