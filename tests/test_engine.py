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


@pytest.mark.parametrize("bpm,seed", [(150, 31), (128, 53)])
def test_quiet_entrance_and_bright_attack_regression(engine, tmp_path, bpm, seed):
    source = tmp_path/"arrangement.wav"
    truth = synthesize(source, kind="arrangement", duration=16, bpm=bpm, seed=seed)
    g = engine.analyze(source)
    boundaries = np.array([s.start_s for s in g.sections[1:]])
    assert len(boundaries) == 3
    assert np.max(np.min(np.abs(np.array(truth["boundaries_s"])[:, None]-boundaries), axis=1)) < 0.5
    bright_ids = {s.id for s in g.sound_objects if s.name == "Bright pulse"}
    bright = [o for o in g.occurrences if o.sound_object_id in bright_ids]
    assert len(bright) >= 15
    assert sum(o.start_s < 3.8 for o in bright) == 0
    arrays = engine.arrays(g.track_id)
    assert arrays["section_similarity"].shape == (len(g.sections), len(g.sections))
    np.testing.assert_allclose(arrays["section_similarity"], arrays["section_similarity"].T)


def test_source_rate_metrics_and_gain_preservation(engine, tmp_path):
    path = tmp_path/"loud.wav"
    sr = 48000
    pcm = np.tile([1.1, -1.1, 0.4, -0.4], sr//2)
    sf.write(path, pcm, sr, subtype="FLOAT")
    g = engine.analyze(path)
    metrics = g.evidence[0].measurements
    assert g.sample_rate == sr
    assert metrics["sample_peak_dbfs"] > 0
    assert metrics["samples_at_or_above_full_scale"] == len(pcm)/2
    assert metrics["stereo_correlation"] is None


def test_nonfinite_and_excess_channels_fail_before_analysis(engine, tmp_path):
    path = tmp_path/"bad.wav"
    pcm = np.zeros(22050)
    pcm[100] = np.nan
    sf.write(path, pcm, 22050, subtype="FLOAT")
    with pytest.raises(ValueError, match="non-finite"):
        engine.analyze(path)
    sf.write(path, np.zeros((22050, 4)), 22050)
    with pytest.raises(ValueError, match="mono or stereo"):
        engine.analyze(path)
    assert not list(engine.root.glob("*/.analysis-*"))


def test_pipeline_upgrade_keeps_old_library_and_versioned_evidence(engine, tmp_path, monkeypatch):
    source = tmp_path/"a.wav"
    synthesize(source, kind="pulse", duration=4)
    old = engine.analyze(source)
    monkeypatch.setattr("genome.engine.ANALYSIS_ID", "dsp-test-next")
    assert engine.load(old.track_id) == old
    assert engine.list_tracks()[0]["new_analysis_available"]
    new = engine.analyze(source)
    assert new.analysis_id == "dsp-test-next"
    assert engine.load(old.track_id, old.analysis_id) == old
    assert engine.load(new.track_id) == new
    assert len(engine.list_tracks()) == 1


def test_fixture_bytes_are_reproducible(tmp_path):
    a, b = tmp_path/"first.wav", tmp_path/"second.wav"
    synthesize(a, duration=2, seed=51)
    synthesize(b, duration=2, seed=51)
    assert a.read_bytes() == b.read_bytes()
    assert b"PEAK" not in a.read_bytes()[:200]


@pytest.mark.parametrize("seed", [3, 31, 72])
def test_stationary_noise_is_not_a_beat_or_recurring_pattern(engine, tmp_path, seed):
    source = tmp_path/"noise.wav"
    synthesize(source, duration=8, kind="noise", seed=seed)
    g = engine.analyze(source)
    assert g.tempo.preferred_bpm is None
    assert not g.patterns
