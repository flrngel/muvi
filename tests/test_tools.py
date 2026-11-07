import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from PIL import Image

from genome.engine import Engine
from genome.fixtures import synthesize
from genome.server import create_app
from genome.tools import MusicTools


@pytest.fixture(scope="module")
def analyzed(tmp_path_factory):
    root = tmp_path_factory.mktemp("tools")
    source = root/"arrangement.wav"
    synthesize(source)
    engine = Engine(root/"store")
    return MusicTools(engine), engine.analyze(source)


def test_digest_references_and_bounded_context(analyzed):
    tools, g = analyzed
    result = tools.get_track_digest(g.track_id)
    assert len(result["digest_text"]) < 8000
    assert "beat_times_s" not in result["tempo"]
    assert set(result["evidence_ids"]) <= {e.id for e in g.evidence}
    assert result["analysis_id"] == g.analysis_id
    assert g.patterns


def test_sound_sections_and_comparison(analyzed):
    tools, g = analyzed
    found = tools.find_sound(g.track_id, "bass")
    assert found["matches"]
    sound = tools.get_sound(g.track_id, found["matches"][0]["sound_object_id"], limit=1)
    assert len(sound["occurrences"]) == 1
    section = tools.get_section(g.track_id, g.sections[0].id, "detail")
    assert all(o["start_s"] < section["time_span"]["end_s"] for o in section["occurrences"])
    comparison = tools.compare_sections(g.track_id, g.sections[0].id, g.sections[0].id)
    assert all(x == 0 for x in comparison["band_energy_delta_db"].values())
    assert not comparison["new_objects"]


def test_crop_preserves_samples_and_coordinates(analyzed):
    tools, g = analyzed
    crop = tools.get_audio_crop(g.track_id, 1.234, 2.135)
    from urllib.parse import unquote, urlparse
    path = Path(unquote(urlparse(crop["audio"]["uri"]).path).lstrip("/") if __import__("os").name == "nt" else unquote(urlparse(crop["audio"]["uri"]).path))
    pcm, sr = sf.read(path, always_2d=True)
    original, _ = sf.read(tools.engine.directory(g.track_id)/"audio/source.wav", always_2d=True)
    first, last = crop["first_sample"], crop["end_sample_exclusive"]
    np.testing.assert_array_equal(pcm, original[first:last])
    assert crop["time_span"]["start_s"] == first/sr


def test_tile_matches_json(analyzed):
    tools, g = analyzed
    packet = tools.render_tile(g.track_id, 1, 6)
    directory = tools.engine.directory(g.track_id)
    image = next(directory.glob("images/*.png"))
    legend = json.loads(image.with_suffix(".json").read_text())
    assert Image.open(image).size == (1600, 900)
    assert legend["analysis_id"] == packet["analysis_id"]
    assert legend["time_span"] == packet["time_span"]


def test_abstention_and_invalid_evidence(analyzed):
    tools, g = analyzed
    assert tools.verify_hypothesis(g.track_id, "independent_bass")["verdict"] == "indeterminate"
    assert tools.verify_hypothesis(g.track_id, "instrument_identity")["verdict"] == "indeterminate"
    assert tools.get_master_metrics(g.track_id)["measurements"]["integrated_lufs"] is None
    with pytest.raises(KeyError):
        tools.get_evidence(g.track_id, ["invented"])
    with pytest.raises(ValueError):
        tools.get_audio_crop(g.track_id, -1, 2)
    with pytest.raises(ValueError):
        tools.call("get_audio_crop", {"track_id": g.track_id, "start_s": float("nan"), "end_s": 2})


def test_concurrent_cache_is_atomic(tmp_path):
    source = tmp_path/"a.wav"
    synthesize(source, duration=4, kind="pulse")
    engine = Engine(tmp_path/"store")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(engine.analyze, [source, source]))
    assert results[0] == results[1]
    assert len(engine.list_tracks()) == 1
    assert not list(engine.root.glob("*/.analysis-*"))


def test_http_upload_jobs_security_and_tool_contract(tmp_path):
    source = tmp_path/"pulse.wav"
    synthesize(source, duration=4, kind="pulse")
    with TestClient(create_app(tmp_path/"store")) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.post("/api/demo", headers={"Origin": "https://example.com"}).status_code == 403
        assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
        assert client.post("/api/tools/analyze_track", json={"arguments": {"path": "secret"}}).status_code == 404
        result = client.post("/api/upload", files={"file": ("pulse.wav", source.read_bytes(), "audio/wav")})
        assert result.status_code == 202
        for _ in range(100):
            job = client.get(f"/api/jobs/{result.json()['job_id']}").json()
            if job["status"] in ("complete", "failed"):
                break
            time.sleep(0.05)
        assert job["status"] == "complete", job
        track_id = job["track_id"]
        assert len(client.get("/api/tracks").json()["tracks"]) == 1
        assert client.get(f"/api/tracks/{track_id}/visuals").json()["analysis_id"]
        packet = client.post("/api/tools/get_track_digest", json={"arguments": {"track_id": track_id}})
        assert packet.status_code == 200
        audio = client.get(f"/api/tracks/{track_id}/artifacts/audio/preview.wav", headers={"Range": "bytes=0-99"})
        assert audio.status_code == 206
        assert client.get(f"/api/tracks/{track_id}/artifacts/%2E%2E/%2E%2E/secret.json").status_code == 404
        assert client.post("/api/upload", files={"file": ("empty.wav", b"")}).status_code == 422

