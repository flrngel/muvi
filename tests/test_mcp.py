import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from genome.fixtures import synthesize


def test_real_mcp_initialize_list_analyze_and_evidence(tmp_path):
    path = tmp_path/"mcp.wav"
    synthesize(path, kind="pulse", duration=4)
    async def run():
        params = StdioServerParameters(command=sys.executable,
                                       args=["-m", "genome.cli", "mcp", "--data-dir", str(tmp_path/"store")])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                assert {"analyze_track", "get_track_digest", "render_tile", "list_tracks"} <= {t.name for t in listed.tools}
                result = await session.call_tool("analyze_track", {"path": str(path)})
                assert not result.isError
                payload = result.structuredContent
                # FastMCP versions may wrap a dict return in `result`.
                payload = payload.get("result", payload)
                digest = await session.call_tool("get_track_digest", {"track_id": payload["track_id"]})
                assert not digest.isError
                missing = await session.call_tool("get_evidence", {"track_id": payload["track_id"], "evidence_ids": ["fake"]})
                assert missing.isError
    asyncio.run(run())

