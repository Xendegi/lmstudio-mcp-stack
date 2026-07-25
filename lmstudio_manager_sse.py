import os
import sys

for _var in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
    os.environ.pop(_var, None)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lmstudio_manager import mcp, ensure_all_files, get_config, _aux_unload_watchdog
from mcp.server.fastmcp.server import TransportSecuritySettings
import threading

HOST = os.environ.get("LMGR_SSE_HOST", "0.0.0.0")
PORT = int(os.environ.get("LMGR_SSE_PORT", "8765"))

ensure_all_files()
config = get_config()
if config.get("auto_unload_aux", True):
    t = threading.Thread(target=_aux_unload_watchdog, daemon=True)
    t.start()
    print(f"[auto-unload] Watchdog started", flush=True)

mcp.settings.host = HOST
mcp.settings.port = PORT
mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
    allowed_hosts=[],
    allowed_origins=[],
)

print(f"[SSE] lmstudio-manager listening on {HOST}:{PORT}", flush=True)
mcp.run(transport="sse")
