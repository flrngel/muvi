import hashlib

import numpy as np
import pytest
import soundfile as sf

from genome.engine import Engine
from genome.fixtures import synthesize
from genome.schema import Genome


@pytest.fixture
def engine(tmp_path):
    return Engine(tmp_path / "store")


@pytest.mark.parametrize("bpm", [90, 120, 150, 180])
def test_clean_pulse_timing_and_tempo(engine, tmp_path, bpm):
    source = tmp_path / "pulse.wav"
    truth = synthesize(source, bpm=bpm, duration=12, kind="pulse")
    result = engine.analyze(source)
    arrays = engine.arrays(result.track_id)
    onsets = arrays["times_s"][arrays["onset_frames"]]
    distances = np.abs(np.array(truth["onsets_s"])[:, None] - onsets)
    assert np.mean(distances.min(axis=1) < 0.05) >= 0.9
    assert np.mean(distances.min(axis=0) < 0.05) >= 0.9
    assert np.median(distances.min(axis=1)) <= 0.025
    assert min(abs(t-bpm)/bpm for t in result.tempo.candidates_bpm) < 0.03


def test_silence_abstains(engine, tmp_path):
    source = tmp_path / "silence.wav"
    synthesize(source, duration=4, kind="silence")
    result = engine.analyze(source)
    assert not result.sound_objects
    assert not result.occurrences
    assert result.tempo.preferred_bpm is None
    assert all(c.verdict == "indeterminate" for c in result.claims)
    assert "NaN" not in result.model_dump_json()


def test_noise_never_proves_sources(engine, tmp_path):
    source = tmp_path / "noise.wav"
    synthesize(source, duration=4, kind="noise")
    result = engine.analyze(source)
    assert all(s.source_status == "unresolved" for s in result.sound_objects)
    assert all(s.source_candidates == ["unknown"] or s.form == "noisy_or_pitched_sustained"
               for s in result.sound_objects)


def test_roundtrip_original_and_cache(engine, tmp_path, monkeypatch):
    source = tmp_path / "test.wav"
    synthesize(source, duration=8)
    first = engine.analyze(source)
    assert Genome.model_validate_json(first.model_dump_json()) == first
    assert hashlib.sha256(source.read_bytes()).hexdigest() == first.source_sha256
    assert (engine.directory(first.track_id) / "audio/original").read_bytes() == source.read_bytes()
    pcm, sr = sf.read(source, always_2d=True)
    stored, stored_sr = sf.read(engine.directory(first.track_id) / "audio/source.wav", always_2d=True)
    assert sr == stored_sr == first.sample_rate
    np.testing.assert_array_equal(pcm, stored)
    def forbidden(*args, **kwargs):
        raise AssertionError("Cache should not re-extract")
    monkeypatch.setattr("genome.engine.extract", forbidden)
    assert engine.analyze(source) == first


def test_shift_moves_events(engine, tmp_path):
    a, b = tmp_path/"a.wav", tmp_path/"b.wav"
    synthesize(a, kind="pulse", duration=7)
    pcm, sr = sf.read(a)
    sf.write(b, np.concatenate([np.zeros((sr, 2)), pcm]), sr, subtype="FLOAT")
    ga, gb = engine.analyze(a), engine.analyze(b)
    aa, ab = engine.arrays(ga.track_id), engine.arrays(gb.track_id)
    ta, tb = aa["times_s"][aa["onset_frames"]], ab["times_s"][ab["onset_frames"]]
    assert np.max(np.abs(ta + 1 - tb)) < 0.025


def test_antiphase_does_not_disappear(engine, tmp_path):
    source = tmp_path/"antiphase.wav"
    synthesize(source, kind="antiphase", duration=5)
    result = engine.analyze(source)
    assert result.mono_policy.startswith("highest_energy_channel")
    assert len(result.occurrences) > 4
    metrics = next(e for e in result.evidence if e.kind == "source_metrics")
    assert metrics.measurements["stereo_correlation"] == pytest.approx(-1)


def test_invalid_and_short_audio(engine, tmp_path):
    source = tmp_path/"fake.wav"
    source.write_text("not audio")
    with pytest.raises(ValueError, match="decode"):
        engine.analyze(source)
    sf.write(source, np.zeros(2205), 22050)
    assert engine.analyze(source).duration_s == 0.1
    with pytest.raises(ValueError):
        engine.load("../../secret")

