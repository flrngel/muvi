"""Run with an isolated wheel environment, outside the repository working directory."""

import json
import tempfile
from pathlib import Path

import genome
from fastapi.testclient import TestClient

from genome.fixtures import synthesize
from genome.server import create_app

repository = Path(__file__).resolve().parents[1]
module_path = Path(genome.__file__).resolve()
assert not module_path.is_relative_to(repository), "This must test the installed wheel, not the checkout"
with tempfile.TemporaryDirectory(prefix="muvi-wheel-smoke-") as temp:
    root = Path(temp)
    source = root/"pulse.wav"
    synthesize(source, duration=4, kind="pulse")
    with TestClient(create_app(root/"store")) as client:
        assert client.get("/api/health").json()["version"] == genome.__version__
        assert b"Music, made legible" in client.get("/").content
        assert client.get("/app.js").status_code == 200
        g = client.app.state.engine.analyze(source)
        assert g.parameters["tempo_autocorrelation"] == "mean_centered_gaussian_lag_smoothing"
        response = client.post("/api/tools/get_track_digest", json={"arguments": {"track_id": g.track_id}})
        assert response.status_code == 200
        assert response.json()["analysis_id"] == g.analysis_id
        assert client.get(f"/api/tracks/{g.track_id}/artifacts/audio/preview.wav").status_code == 200
        assert client.get("/api/tools").json()["mcp_config"]["mcpServers"]["muvi"]["args"][:2] == ["-m", "genome.cli"]
print(json.dumps({"version": genome.__version__, "installed_module": str(module_path),
                  "result": "passed: packaged UI, API, audio analysis, digest, preview and MCP configuration"}))
