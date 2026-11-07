from mcp.server.fastmcp import FastMCP
from typing import Any

from genome.engine import Engine
from genome.tools import MusicTools, SYSTEM_PROMPT


def create_mcp(root=None):
    server = FastMCP("Muvi Music Genome", instructions=SYSTEM_PROMPT)
    tools = MusicTools(Engine(root))
    for name, fn in tools.registry().items():
        server.add_tool(fn, name=name, description=fn.__doc__, structured_output=True)

    @server.tool()
    def list_tracks() -> dict[str, Any]:
        """List analyzed tracks in this local library before retrieving a track digest."""
        return {"tracks": tools.engine.list_tracks()}

    return server

