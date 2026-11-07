import json

import pytest

from genome.engine import Engine
from genome.evaluate import onset_metrics
from genome.rhythm import pulse_summary
from genome.schema import Genome
from genome.tools import MusicTools
from scripts.beat_cases import make_case


@pytest.mark.parametrize('kind,bpm', [('steady', 120), ('missing', 137), ('change', 96),
                                   ('break', 128), ('noise', 115), ('swing', 112),
                                   ('drift', 90), ('subdivisions', 150)])
def test_development_rhythm_counterexamples(tmp_path, kind, bpm):
    path = tmp_path/'anonymous.wav'
    truth = make_case(path, kind, bpm, .37, 401)
    engine = Engine(tmp_path/'store')
    g = engine.analyze(path)
    tools = MusicTools(engine)
    r = tools.get_rhythm(g.track_id, limit=500)
    assert r['available'] and r['meter_status'] == r['downbeat_status'] == 'not_estimated'
    if kind != 'noise':
        assert onset_metrics(truth['pulse_times_s'], r['onset_times_s'])['f1'] >= .95
    else:
        assert r['pulse']['pulse_rate_bpm'] is None
        assert r['track_timing_status'] == 'irregular_or_insufficient'
    for probe in truth['local_rates']:
        local = tools.get_rhythm(g.track_id, probe['start_s'], probe['end_s'])
        rate = local['pulse']['pulse_rate_bpm']
        if probe['bpm'] is None:
            assert rate is None
        else:
            assert abs(rate-probe['bpm'])/probe['bpm'] < .05
    if kind in ('change', 'drift'):
        assert r['track_timing_status'] == 'varying'
    if kind in ('steady', 'subdivisions'):
        assert r['track_timing_status'] == 'steady'
    if kind == 'break':
        assert len(r['long_gaps']) == 1
        gap = r['long_gaps'][0]
        assert abs(gap['start_s']-truth['long_gaps'][0]['start_s']) < .05
        assert any(p['support'] == 'extrapolated' and gap['start_s'] < p['time_s'] < gap['end_s']
                   for p in r['global_grid_preview'])
    assert tools.get_evidence(g.track_id, r['evidence_ids'])['evidence'][0]['kind'] == 'rhythm_stream'
    assert Genome.model_validate_json(g.model_dump_json()) == g


def test_paging_span_validation_and_legacy_abstention(tmp_path):
    path = tmp_path/'pulse.wav'
    make_case(path, 'steady', 120, .37, 401)
    engine = Engine(tmp_path/'store')
    tools = MusicTools(engine)
    g = engine.analyze(path)
    first = tools.get_rhythm(g.track_id, limit=3)
    second = tools.get_rhythm(g.track_id, offset=3, limit=3)
    assert max(first['onset_times_s']) < min(second['onset_times_s'])
    with pytest.raises(ValueError):
        tools.get_rhythm(g.track_id, -1, 3)
    with pytest.raises(ValueError):
        tools.call('get_rhythm', {'track_id':g.track_id, 'band':'bass'})
    # A genuine old schema remains readable and never receives invented rhythm data.
    data = g.model_dump()
    data.pop('rhythm')
    data['schema_version'] = '0.1.0'
    (engine.directory(g.track_id)/'genome.json').write_text(json.dumps(data), encoding='utf-8')
    legacy = tools.get_rhythm(g.track_id)
    assert not legacy['available'] and legacy['measurement_status'] == 'not_available'


def test_quantized_long_steady_pulse_does_not_fake_phase_drift():
    times = [round((.37+i*.4)*22050/256)*256/22050 for i in range(600)]
    pulse = pulse_summary(times)
    assert abs(pulse.pulse_rate_bpm-150) < .05
    assert pulse.phase_concentration > .99
