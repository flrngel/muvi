from mcp.server.fastmcp import FastMCP
from typing import Any
import re

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

    @server.resource("muvi://tracks/{track_hash}/{analysis_id}/genome", mime_type="application/json")
    def genome_resource(track_hash: str, analysis_id: str) -> str:
        """The validated canonical genome for an analyzed track."""
        return tools.engine.load(track_hash, analysis_id).model_dump_json()

    @server.resource("muvi://tracks/{track_hash}/{analysis_id}/images/{tile_key}", mime_type="image/png")
    def image_resource(track_hash: str, analysis_id: str, tile_key: str) -> bytes:
        """A rendered synchronized evidence image, created by render_tile."""
        if not re.fullmatch(r"[a-f0-9]{20}", tile_key):
            raise ValueError("Invalid image key")
        tools.engine.load(track_hash, analysis_id)
        return (tools.engine.directory(track_hash, analysis_id)/f"images/tile-{tile_key}.png").read_bytes()

    @server.resource("muvi://tracks/{track_hash}/{analysis_id}/clips/{crop_key}", mime_type="audio/wav")
    def crop_resource(track_hash: str, analysis_id: str, crop_key: str) -> bytes:
        """An original-mixture audio crop, created by get_audio_crop."""
        if not re.fullmatch(r"[a-f0-9]{20}", crop_key):
            raise ValueError("Invalid crop key")
        tools.engine.load(track_hash, analysis_id)
        return (tools.engine.directory(track_hash, analysis_id)/f"clips/{crop_key}.wav").read_bytes()

    return server

