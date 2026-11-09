import json

import numpy as np
import pytest
import soundfile as sf

from genome.engine import Engine
from genome.evaluate import onset_metrics
from genome.schema import Genome
from genome.tools import MusicTools
from scripts.beat_cases import make_case
from tests.test_cli import invoke, packet


@pytest.mark.parametrize('kind,bpm', [('steady', 120), ('swing', 112), ('subdivisions', 150),
                                    ('change', 96), ('drift', 90)])
def test_tracked_timing_against_known_audio_events(tmp_path, kind, bpm):
    audio = tmp_path/'probe.wav'
    truth = make_case(audio, kind, bpm, .37, 401)
    engine = Engine(tmp_path/'library')
    g = engine.analyze(audio)
    bt = g.beat_tracking
    assert bt.status == 'inferred'
    score = onset_metrics(truth['pulse_times_s'], [b.time_s for b in bt.beats], .07)
    assert score['f1'] >= .9
    assert score['median_error_s'] < .02
    for probe in truth['local_rates']:
        result = MusicTools(engine).get_beats(g.track_id, probe['start_s'], probe['end_s'])
        assert result['status'] == 'inferred'
        assert abs(result['local_tempo_bpm']-probe['bpm'])/probe['bpm'] < .06


@pytest.mark.parametrize('kind', ['noise', 'silence'])
def test_negative_controls_abstain(tmp_path, kind):
    audio = tmp_path/'negative.wav'
    if kind == 'noise':
        make_case(audio, 'noise', 115, .37, 401)
    else:
        sf.write(audio, np.zeros(22050*12), 22050)
    engine = Engine(tmp_path/'library')
    g = engine.analyze(audio)
    result = MusicTools(engine).get_beats(g.track_id)
    assert result['tracking_status'] == result['status'] == 'unresolved'
    assert result['local_tempo_bpm'] is None and result['beats'] == []


@pytest.mark.parametrize('kind,bpm', [('missing', 137), ('break', 128)])
def test_missing_attacks_are_labelled_and_silent_window_abstains(tmp_path, kind, bpm):
    audio = tmp_path/'gaps.wav'
    truth = make_case(audio, kind, bpm, .37, 401)
    engine = Engine(tmp_path/'library')
    g = engine.analyze(audio)
    bt = g.beat_tracking
    assert any(b.support == 'interpolated' for b in bt.beats)
    supported = [b.time_s for b in bt.beats if b.support == 'onset_supported']
    assert onset_metrics(truth['pulse_times_s'], supported, .07)['f1'] >= .95
    if kind == 'break':
        result = MusicTools(engine).get_beats(g.track_id, 8, 11)
        assert result['status'] == 'unresolved' and result['local_tempo_bpm'] is None
        assert result['unsupported_spans'] and result['onset_supported_count'] == 0


def test_beat_cli_paging_provenance_legacy_and_validation(tmp_path):
    audio = tmp_path/'pulse.wav'
    make_case(audio, 'steady', 120, .37, 401)
    engine = Engine(tmp_path/'library')
    g = engine.analyze(audio)
    first = packet(engine.root, 'beats', g.track_id, '--start', 2, '--end', 8, '--limit', 2)
    second = packet(engine.root, 'beats', g.track_id, '--start', 2, '--end', 8, '--limit', 2, '--offset', 2)
    assert first['beat_count'] > 2 and first['next_offset'] == 2
    assert second['beats'][0]['time_s'] > first['beats'][-1]['time_s']
    assert first['local_tempo_bpm'] == second['local_tempo_bpm']
    assert all(2 <= b['time_s'] < 8 for b in first['beats'])
    assert first['meter_status'] == first['downbeat_status'] == 'not_estimated'
    evidence = packet(engine.root, 'evidence', g.track_id, *first['evidence_ids'])
    assert any(e['kind'] == 'beat_tracking' for e in evidence['evidence'])
    assert invoke(engine.root, 'beats', g.track_id).stdout
    for arguments in [('--limit', 501), ('--offset', -1), ('--end', 200), ('--start', 8, '--end', 2)]:
        assert 'error' in packet(engine.root, 'beats', g.track_id, *arguments, code=2)
    data = g.model_dump()
    data.pop('beat_tracking')
    data['schema_version'] = '0.2.0'
    (engine.directory(g.track_id)/'genome.json').write_text(json.dumps(data), encoding='utf-8')
    assert not packet(engine.root, 'beats', g.track_id)['available']
    for mutate in ['references', 'order', 'bounds']:
        invalid = g.model_dump()
        bt = invalid['beat_tracking']
        if mutate == 'references':
            bt['evidence_ids'] = ['missing']
        elif mutate == 'order':
            bt['beats'].reverse()
        else:
            bt['beats'][-1]['time_s'] = g.duration_s
        with pytest.raises(ValueError):
            Genome.model_validate(invalid)
