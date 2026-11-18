import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from genome import exports
from genome.engine import Engine
from genome.fixtures import synthesize
from genome.pair import prepare
from genome.tools import MusicTools


def test_gain_control_tracks_frame_power_and_aligned_envelopes(tmp_path):
    path = tmp_path / "pulse.wav"
    synthesize(path, duration=4, kind="pulse")
    pcm, sr = sf.read(path)
    engine = Engine(tmp_path / "store")
    source = engine.analyze(path)
    quiet = tmp_path / "quieter.wav"
    sf.write(quiet, pcm * 0.25, sr, subtype="DOUBLE")
    other = engine.analyze(quiet)
    tools = MusicTools(engine)
    spans = (0.2, 3.82)
    packet = tools.render_pair(source.track_id, other.track_id, spans, spans)
    legend = json.loads(Path(packet["legend"]["path"]).read_text())
    a, b = legend["tracks"].values()
    assert a["gain_db"] == pytest.approx(20 * np.log10(0.25))
    assert b["gain_db"] == 0
    assert a["hit_times_s"] == b["hit_times_s"] and len(a["hit_times_s"]) == 3
    assert set(a["evidence_ids"]["hits"]) <= {e.id for e in source.evidence}
    first, second = [prepare(engine, g, spans, gain, 160) for g, gain in ((source, a["gain_db"]), (other, 0))]
    np.testing.assert_allclose(first["envelopes"], second["envelopes"], atol=0.01)
    for key in ("overview", "power"):
        np.testing.assert_allclose(first[key].clip(-75, -15), second[key].clip(-75, -15), atol=0.01)
    assert first["legend"]["pulse"]["ticks_s"] == pytest.approx([0.2 + i * 0.375 for i in range(6)])
    assert first["legend"]["phrase_s"] == pytest.approx([0.2, 2.45])
    assert packet == tools.render_pair(source.track_id, other.track_id, spans, spans)


def test_old_analysis_without_rhythm_or_beats_and_silent_excerpt(tmp_path):
    source = tmp_path / "quiet.wav"
    synthesize(source, duration=1, kind="silence")
    engine = Engine(tmp_path / "store")
    g = engine.analyze(source)
    g.rhythm = g.beat_tracking = None
    (engine.directory(g.track_id) / "genome.json").write_text(g.model_dump_json(), encoding="utf-8")
    tools = MusicTools(engine)
    result = tools.render_pair(g.track_id, g.track_id, (0.9, 1), (0, 0.5))
    legend = json.loads(Path(result["legend"]["path"]).read_text())
    assert "unmatched" in legend["gain_basis"]
    for info in legend["tracks"].values():
        assert info["hit_times_s"] == info["available_attack_streams"] == info["pulse"]["ticks_s"] == []
        assert info["original_track_rms_dbfs"] is None
    for bounds in [(-1, 0.7), (0.5, 0.51), (0.7, 1.1), (1, 0)]:
        with pytest.raises(ValueError, match="passage"):
            tools.render_pair(g.track_id, g.track_id, bounds, (0, 1))
    with pytest.raises(ValueError, match="tempo"):
        tools.render_pair(g.track_id, g.track_id, (0, 1), (0, 1), bpm_a=float("nan"))


def test_pair_export_rolls_back_partial_overwrite(tmp_path, monkeypatch):
    engine = Engine(tmp_path / "cache")
    keys = ("passage", "phrase", "hits", "legend")
    result = {}
    for key in keys:
        src = engine.root / key
        src.write_bytes(b"new " + key.encode())
        result[key] = {"path": str(src)}
    output = tmp_path / "pair.png"
    output.write_bytes(b"old")
    actual = exports.write

    def fail_at_hits(path, data, force):
        if path.name == "pair-hits.png":
            raise OSError("simulated failure")
        return actual(path, data, force)

    monkeypatch.setattr(exports, "write", fail_at_hits)
    with pytest.raises(OSError, match="simulated failure"):
        exports.export_pair(output, result, engine, True, [])
    assert output.read_bytes() == b"old"
    assert not (tmp_path / "pair-phrase.png").exists()
    assert not (tmp_path / "pair.json").exists()
