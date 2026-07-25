from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

LM_STUDIO_BASE = os.environ.get("LM_STUDIO_BASE", "http://127.0.0.1:1234")
LM_STUDIO_KEY = os.environ.get(
    "LM_STUDIO_API_KEY", "sk-lm-rTgbTGyG:DGJ5nhlDtjok9UFuDtMx"
)

CLIENT = httpx.Client(timeout=httpx.Timeout(10.0, connect=3.0))

_LAST_UNLOADED_MODEL: str | None = None
_LAST_UNLOADED_INSTANCE: str | None = None


@dataclass
class GpuInfo:
    total_mb: int = 0
    used_mb: int = 0
    free_mb: int = 0
    name: str = ""
    driver: str = ""
    error: str = ""


def _nvidia_smi_gpu() -> GpuInfo:
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            return GpuInfo(error=r.stderr.strip())
        parts = [c.strip() for c in r.stdout.strip().split(", ")]
        info = GpuInfo(
            name=parts[0] if len(parts) > 0 else "",
            total_mb=int(parts[1]) if len(parts) > 1 else 0,
            used_mb=int(parts[2]) if len(parts) > 2 else 0,
            free_mb=int(parts[3]) if len(parts) > 3 else 0,
            driver=parts[4] if len(parts) > 4 else "",
        )
        return info
    except FileNotFoundError:
        return GpuInfo(error="nvidia-smi not found")
    except Exception as e:
        return GpuInfo(error=str(e))


def get_gpu_info() -> GpuInfo:
    return _nvidia_smi_gpu()


def get_lm_studio_loaded() -> list[dict[str, Any]]:
    loaded = []
    try:
        r = CLIENT.get(
            f"{LM_STUDIO_BASE}/api/v1/models/",
            headers={"Authorization": f"Bearer {LM_STUDIO_KEY}"},
        )
        if r.status_code != 200:
            return loaded
        for model in r.json().get("models", []):
            for inst in model.get("loaded_instances", []):
                loaded.append({
                    "instance_id": inst.get("id"),
                    "model_key": model.get("key"),
                    "display_name": model.get("display_name"),
                    "context_length": inst.get("config", {}).get("context_length"),
                })
    except Exception:
        pass
    return loaded


def unload_lm_studio(model_key: str | None = None) -> dict[str, Any]:
    global _LAST_UNLOADED_MODEL, _LAST_UNLOADED_INSTANCE
    loaded = get_lm_studio_loaded()
    if not loaded:
        return {"ok": True, "unloaded": [], "message": "Nothing loaded"}
    unloaded = []
    for inst in loaded:
        if model_key and inst["model_key"] != model_key:
            continue
        try:
            r = CLIENT.post(
                f"{LM_STUDIO_BASE}/api/v1/models/unload",
                headers={
                    "Authorization": f"Bearer {LM_STUDIO_KEY}",
                    "Content-Type": "application/json",
                },
                json={"instance_id": inst["instance_id"]},
            )
            if r.status_code == 200:
                _LAST_UNLOADED_MODEL = inst["model_key"]
                _LAST_UNLOADED_INSTANCE = inst["instance_id"]
                unloaded.append(inst["model_key"])
        except Exception:
            pass
    return {"ok": True, "unloaded": unloaded, "message": f"Unloaded {len(unloaded)} model(s)"}


def restore_lm_studio() -> dict[str, Any]:
    global _LAST_UNLOADED_MODEL
    if not _LAST_UNLOADED_MODEL:
        return {"ok": False, "message": "No model to restore"}
    try:
        r = CLIENT.post(
            f"{LM_STUDIO_BASE}/api/v1/models/load",
            headers={
                "Authorization": f"Bearer {LM_STUDIO_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": _LAST_UNLOADED_MODEL},
        )
        if r.status_code == 200:
            model = _LAST_UNLOADED_MODEL
            _LAST_UNLOADED_MODEL = None
            return {"ok": True, "message": f"Restored {model}"}
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def ensure_free_vram(
    required_mb: int = 8000,
    wait_seconds: int = 60,
) -> dict[str, Any]:
    gpu = get_gpu_info()
    if gpu.error:
        return {"ok": False, "error": gpu.error}
    if gpu.free_mb >= required_mb:
        return {"ok": True, "action": "none", "free_mb": gpu.free_mb,
                "message": f"Already free ({gpu.free_mb} MB >= {required_mb} MB)"}
    loaded = get_lm_studio_loaded()
    unloaded_keys = [m["model_key"] for m in loaded if m["model_key"]]
    if unloaded_keys:
        result = unload_lm_studio()
        if not result.get("unloaded"):
            return {"ok": False, "error": "No VRAM and couldn't unload LM Studio models",
                    "free_mb": gpu.free_mb, "required_mb": required_mb}
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            gpu = get_gpu_info()
            if gpu.free_mb >= required_mb:
                return {"ok": True, "action": "unloaded",
                        "unloaded": unloaded_keys,
                        "free_mb": gpu.free_mb,
                        "message": f"Unloaded {', '.join(unloaded_keys)}. Free: {gpu.free_mb} MB"}
            time.sleep(2)
        gpu = get_gpu_info()
        return {"ok": False, "error": f"VRAM still insufficient after {wait_seconds}s",
                "free_mb": gpu.free_mb, "required_mb": required_mb}
    return {"ok": True, "action": "skip",
            "free_mb": gpu.free_mb,
            "message": f"VRAM appears consumed by ComfyUI/other (free: {gpu.free_mb} MB). Proceeding."}


def status() -> dict[str, Any]:
    gpu = get_gpu_info()
    lm = get_lm_studio_loaded()
    return {
        "ok": True,
        "gpu": {
            "name": gpu.name,
            "total_mb": gpu.total_mb,
            "used_mb": gpu.used_mb,
            "free_mb": gpu.free_mb,
        },
        "lm_studio_loaded": lm,
        "last_unloaded": _LAST_UNLOADED_MODEL,
        "platform": platform.platform(),
    }
