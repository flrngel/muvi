import asyncio
import sys
from datetime import timedelta

import pytest

pytest.importorskip("mcp", reason="Install the optional MCP extra to test the stdio adapter")

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
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=45)) as session:
                await session.initialize()
                listed = await session.list_tools()
                assert {"analyze_track", "get_track_digest", "get_beats", "render_tile", "list_tracks"} <= {t.name for t in listed.tools}
                assert len(listed.tools) == 15
                result = await session.call_tool("analyze_track", {"path": str(path)})
                assert not result.isError
                payload = result.structuredContent
                # FastMCP versions may wrap a dict return in `result`.
                payload = payload.get("result", payload)
                digest = await session.call_tool("get_track_digest", {"track_id": payload["track_id"]})
                assert not digest.isError
                beats = await session.call_tool('get_beats', {'track_id': payload['track_id'], 'limit': 3})
                assert not beats.isError
                beat_data = beats.structuredContent.get('result', beats.structuredContent)
                assert beat_data['available'] and beat_data['meter_status'] == 'not_estimated'
                beat_evidence = await session.call_tool('get_evidence', {'track_id': payload['track_id'], 'evidence_ids': beat_data['evidence_ids']})
                assert not beat_evidence.isError
                rhythm = await session.call_tool("get_rhythm", {"track_id": payload["track_id"], "band": "low", "limit": 3})
                assert not rhythm.isError
                data = rhythm.structuredContent.get("result", rhythm.structuredContent)
                assert len(data['onset_times_s']) == 3 and data['next_offset'] == 3
                assert abs(data['pulse']['pulse_rate_bpm']-150) < 4.5
                cited = await session.call_tool('get_evidence', {'track_id': payload['track_id'], 'evidence_ids': data['evidence_ids']})
                assert not cited.isError
                missing = await session.call_tool("get_evidence", {"track_id": payload["track_id"], "evidence_ids": ["fake"]})
                assert missing.isError
                crop = await session.call_tool("get_audio_crop", {"track_id": payload["track_id"], "start_s": 0.2, "end_s": 0.3})
                crop_data = crop.structuredContent.get("result", crop.structuredContent)
                resource = await session.read_resource(crop_data["audio"]["resource_uri"])
                assert resource.contents[0].mimeType == "audio/wav"
                import base64
                assert base64.b64decode(resource.contents[0].blob)[:4] == b"RIFF"
                tile = await session.call_tool("render_tile", {"track_id": payload["track_id"], "start_s": 0, "end_s": 2})
                tile_data = tile.structuredContent.get("result", tile.structuredContent)
                visual = await session.read_resource(tile_data["image"]["resource_uri"])
                assert visual.contents[0].mimeType == "image/png"
                assert base64.b64decode(visual.contents[0].blob)[:8] == b"\x89PNG\r\n\x1a\n"
    asyncio.run(run())

