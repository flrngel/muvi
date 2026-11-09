"""Presentation must preserve timing/support and readable evidence references."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unicodedata

import numpy as np
import pytest
from PIL import Image

from genome.charts import render
from genome.terminal import format_result, table


def scene(tmp_path, duration=8, tracking=True):
    t = np.linspace(0, duration, 401)
    data = {'times_s': t, 'spectrogram_power': np.full((12, len(t)), .001),
            'frequency_edges_hz': np.geomspace(30, 11025, 13),
            'band_power': np.full((3, len(t)), .01), 'onset_strength': np.zeros(len(t))}
    (tmp_path/'images').mkdir(exist_ok=True)
    engine = NS(directory=lambda *a: tmp_path, arrays=lambda *a: data)
    beats = [NS(time_s=.7, support='onset_supported'), NS(time_s=1.4, support='interpolated'),
             NS(time_s=2., support='onset_supported')]
    g = NS(analysis_id='test-analysis', track_id='sha256:'+'a'*64, title='Original mixture',
           tempo=NS(beat_times_s=[.5, 1., 1.5, 2.]),
           beat_tracking=NS(status='inferred', beats=beats) if tracking else None,
           sections=[NS(start_s=0), NS(start_s=1.2)], evidence=[], occurrences=[],
           sound_objects=[NS(id='S01', name='Low transient texture')])
    return engine, g


def observed_save(monkeypatch):
    from matplotlib.figure import Figure
    original = Figure.savefig
    captures = []
    def save(fig, *args, **kwargs):
        captures.append({'texts': [t.get_text() for t in fig.findobj() if hasattr(t, 'get_text')],
                         'markers': {c.get_label(): [s[:, 0].tolist() for s in c.get_segments()]
                                     for c in fig.axes[2].collections if hasattr(c, 'get_segments')}})
        return original(fig, *args, **kwargs)
    monkeypatch.setattr(Figure, 'savefig', save)
    return captures


def test_chart_tracks_actual_beats_and_support_with_new_cache(tmp_path, monkeypatch):
    engine, g = scene(tmp_path)
    old_key = hashlib.sha256(f'{g.analysis_id}:0.000000000:2.000000000:tile-v1'.encode()).hexdigest()[:20]
    old = tmp_path/f'images/tile-{old_key}.png'
    old.write_bytes(b'old preserved artifact')
    old.with_suffix('.json').write_text('{}')
    captures = observed_save(monkeypatch)
    png, companion = render(engine, g, 0, 2)
    assert Path(png).name != old.name
    assert old.read_bytes() == b'old preserved artifact'
    legend = json.loads((tmp_path/companion).read_text())
    assert legend['beat_overlay']['beats'] == [
        {'time_s': .7, 'support': 'onset_supported'}, {'time_s': 1.4, 'support': 'interpolated'}]
    assert captures[0]['markers']['Onset-supported'] == [[.7, .7]]
    assert captures[0]['markers']['Interpolated'] == [[1.4, 1.4]]
    assert 'Digital power (dB)' in captures[0]['texts']
    assert any('S01' in t and 'Low transient texture' in t for t in captures[0]['texts'])
    assert legend['object_labels'] == {'S01': 'Low transient texture'}
    assert Image.open(tmp_path/png).size == (1600, 900)
    assert render(engine, g, 0, 2) == (png, companion)
    assert len(captures) == 1


@pytest.mark.parametrize('tracking', [False, True])
def test_chart_never_fills_missing_or_silent_tracking_with_grid(tmp_path, monkeypatch, tracking):
    engine, g = scene(tmp_path, tracking=tracking)
    if tracking:
        g.beat_tracking.beats = []
        g.beat_tracking.status = 'unresolved'
    captures = observed_save(monkeypatch)
    _, companion = render(engine, g, 0, 2)
    legend = json.loads((tmp_path/companion).read_text())
    assert legend['beat_overlay']['beats'] == []
    assert not captures[0]['markers']
    assert any('unavailable' in t.lower() or 'no tracked' in t.lower() for t in captures[0]['texts'])


def test_overview_declares_omissions_and_retains_coordinates(tmp_path, monkeypatch):
    engine, g = scene(tmp_path, duration=80)
    g.beat_tracking.beats = [NS(time_s=i*.5, support='onset_supported') for i in range(160)]
    g.sections = [NS(start_s=i*2) for i in range(40)]
    captures = observed_save(monkeypatch)
    _, companion = render(engine, g, 0, 80)
    legend = json.loads((tmp_path/companion).read_text())
    assert len(legend['beat_overlay']['beats']) == 160
    assert legend['beat_overlay']['displayed_count'] == 0
    assert legend['section_overlay']['displayed_count'] <= 24
    assert len(legend['section_overlay']['times_s']) == 39
    assert not captures[0]['markers']
    assert any('160' in t and 'omitted' in t for t in captures[0]['texts'])


def cells(text):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in text)


@pytest.mark.parametrize('columns', [80, 120])
def test_terminal_preserves_unicode_values_and_wraps_prose(monkeypatch, columns):
    monkeypatch.setenv('COLUMNS', str(columns))
    token = 'W'+'1234567890abcdef'*12
    title = '한글 제목 Cafe\u0301 '
    output = table(['VALUE'], [[title*4], [token]])
    assert all(cells(line) <= columns for line in output.splitlines())
    assert token in ''.join(output.split())
    assert ''.join((title*4).split()) in ''.join(output.split())
    prose = format_result('verify', {'verdict':'indeterminate', 'conclusion':title*20,
                                    'evidence_ids':[token], 'next_check':'Check each original time span. '*10})
    assert all(cells(line) <= columns for line in prose.splitlines())
    assert token in ''.join(prose.split())
    assert '\x1b' not in table(['TITLE'], [['untrusted\x1b[31m title']])


def test_terminal_flow_rows_and_ending_have_resolvable_ids(monkeypatch):
    monkeypatch.setenv('COLUMNS', '80')
    item = {'id':'FLOW_001', 'start_s':0, 'end_s':12, 'description':'A sustained measured texture.', 'similar_to':None}
    ending = {**item, 'id':'FLOW_014', 'start_s':90, 'end_s':100}
    data = {'title':'Demo', 'duration_s':100, 'track_id':'sha256:'+'a'*64, 'analysis_id':'analysis',
            'tempo':{'preferred_bpm':None, 'candidates_bpm':[]}, 'sections':[], 'prominent_objects':[],
            'sections_truncated':False, 'flow':{'items':[item], 'next_offset':12, 'ending':ending},
            'patterns':[], 'warnings':[]}
    output = format_result('inspect', data)
    assert 'FLOW_001' in output and 'Ending FLOW_014' in output
    assert all(cells(line) <= 80 for line in output.splitlines())
