from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from vram_manager_core import (
    ensure_free_vram,
    get_gpu_info,
    get_lm_studio_loaded,
    restore_lm_studio,
    status,
    unload_lm_studio,
)

mcp = FastMCP("vram-manager")


@mcp.tool()
def status_vram() -> dict[str, Any]:
    return status()


@mcp.tool()
def ensure_vram(
    required_mb: int = 8000,
    wait_seconds: int = 60,
) -> dict[str, Any]:
    return ensure_free_vram(required_mb, wait_seconds)


@mcp.tool()
def unload_lm_studio_model(model_key: str = "") -> dict[str, Any]:
    return unload_lm_studio(model_key or None)


@mcp.tool()
def restore_lm_studio_model() -> dict[str, Any]:
    return restore_lm_studio()


@mcp.tool()
def list_loaded() -> list[dict[str, Any]]:
    return get_lm_studio_loaded()


def main() -> None:
    info = get_gpu_info()
    if info.error:
        print(f"[vram-manager] {info.error}")
    else:
        print(f"[vram-manager] GPU: {info.name}, "
              f"VRAM: {info.used_mb}/{info.total_mb} MB used, "
              f"{info.free_mb} MB free")
    mcp.run()


if __name__ == "__main__":
    main()
