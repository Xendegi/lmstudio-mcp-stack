import os
import sys

for _var in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
    os.environ.pop(_var, None)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp.server import TransportSecuritySettings
from vram_manager import mcp

HOST = os.environ.get("VRAM_SSE_HOST", "0.0.0.0")
PORT = int(os.environ.get("VRAM_SSE_PORT", "8767"))

mcp.settings.host = HOST
mcp.settings.port = PORT
mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
    allowed_hosts=[],
    allowed_origins=[],
)

print(f"[SSE] vram-manager listening on {HOST}:{PORT}", flush=True)
mcp.run(transport="sse")
