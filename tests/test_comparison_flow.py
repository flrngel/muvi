import json
import subprocess
import sys

import numpy as np
import pytest
import soundfile as sf

from genome.engine import Engine
from genome.schema import Section
from genome.tools import MusicTools
from tests.test_cli import invoke, packet


@pytest.fixture(scope='module')
def measured(tmp_path_factory):
    root = tmp_path_factory.mktemp('comparison')
    sr = 22050
    t = np.arange(12*sr)/sr
    pcm = .2*np.sin(2*np.pi*80*t)
    pcm[4*sr:8*sr] *= .5
    pcm[8*sr:] = 0
    source = root/'levels.wav'
    sf.write(source, pcm, sr, subtype='PCM_24')
    engine = Engine(root/'library')
    return engine, engine.analyze(source)


def test_exact_comparison_gain_reverse_identity_and_inline_evidence(measured):
    engine, g = measured
    tools = MusicTools(engine)
    a, b = [.371, 3.713], [4.371, 7.713]
    forward = tools.compare_sections(g.track_id, range_a=a, range_b=b)
    reverse = tools.compare_sections(g.track_id, range_a=b, range_b=a)
    same = tools.compare_sections(g.track_id, range_a=a, range_b=a)
    assert forward['window_a']['time_span'] == dict(start_s=a[0],end_s=a[1])
    assert forward['window_b']['time_span'] == dict(start_s=b[0],end_s=b[1])
    change = forward['changes']['band_power']['low']
    assert change['delta_db'] == pytest.approx(-6.0206, abs=.02)
    assert change['direction'] == 'decreased'
    assert reverse['changes']['band_power']['low']['delta_db'] == pytest.approx(-change['delta_db'])
    assert same['changes']['band_power']['low']['delta_db'] == 0
    assert same['changes']['band_power']['low']['direction'] == 'unchanged'
    assert abs(forward['window_a']['bands']['low']['fraction']-forward['window_b']['bands']['low']['fraction']) < .001
    assert forward['changes']['source_rms_dbfs']['delta'] == pytest.approx(-6.0206, abs=.02)
    assert len(forward['evidence']) == 2
    for ev, span in zip(forward['evidence'], (a,b)):
        assert (ev['start_s'],ev['end_s']) == tuple(span)
        assert ev == next(e for e in tools.get_evidence(g.track_id,[ev['id']])['evidence'] if e['id']==ev['id'])


def test_zero_and_missing_spectral_frames_are_distinct(measured):
    engine,g = measured
    tools=MusicTools(engine)
    silence=tools.compare_sections(g.track_id,range_a=[.371,3.713],range_b=[8.371,11.713])
    assert silence['window_b']['source_activity']=='digital_silence'
    assert silence['changes']['band_power']['low']['status']=='to_zero'
    assert silence['changes']['band_power']['low']['delta_db'] is None
    assert silence['changes']['source_rms_dbfs']['delta'] is None
    tiny=tools.compare_sections(g.track_id,range_a=[.001,.002],range_b=[8.001,8.002])
    assert tiny['window_a']['source_activity']=='signal_present'
    assert tiny['changes']['band_power']['low']['status']=='unavailable'
    assert json.dumps(tiny,allow_nan=False)


def test_rate_normalization_and_opposite_band_directions():
    from genome.comparison import compare_windows
    def window(duration,counts):
        return {'time_span':{'start_s':0,'end_s':duration},'bands':{b:{'mean_power':1} for b in ('low','mid','high')},
                'band_attacks':{b:{'event_count':n} for b,n in zip(('low','mid','high'),counts)},
                'attack_density_per_s':2,'source_rms_dbfs':-10,'energy_weighted_centroid_hz':500,'harmonic_like_ratio':.5}
    changes=compare_windows(window(2,[4,4,4]),window(4,[4,8,12]))
    assert changes['band_attack_density_per_s']['low']['delta']==-1
    assert changes['band_attack_density_per_s']['mid']['delta']==0
    assert changes['band_attack_density_per_s']['high']['delta']==1
    assert changes['band_attack_density_per_s']['high']['direction']=='increased'


def section(i,power,attacks=10,group='A'):
    return Section(id=f'SEC_{i:02}',start_s=i*5,end_s=(i+1)*5,structure_group=group,
                   evidence_ids=[f'E{i}'],mean_band_power=power,onset_count=attacks)


def test_flow_uses_absolute_measurements_and_covers_returns():
    from genome.flow import summarize_flow
    sections=[section(0,[1,.01,.001]),section(1,[1.1,.011,.0011]),
              section(2,[0,1,.1],0),section(3,[0,0,0],0),section(4,[1,.01,.001])]
    flow=summarize_flow(sections,25)
    items=flow['items']
    assert len(items)==4 and flow['next_offset'] is None
    assert items[0]['start_s']==0 and items[-1]['end_s']==25
    assert items[0]['section_ids']==['SEC_00','SEC_01']
    assert items[1]['dominant_band']=='mid' and items[1]['attack_density_per_s']==0
    assert items[1]['total_mean_power']>0
    assert items[2]['total_mean_power']==0
    assert items[2]['similar_to'] is None  # all sections deliberately have the same group
    assert items[-1]['similar_to']['flow_id']==items[0]['id']
    assert items[1]['change_from_previous']['band_power']['low']['direction']=='decreased'
    assert flow['ending']['end_s']==25
    assert 'source silence' in flow['limitation']


def test_flow_pagination_and_drift_do_not_hide_the_ending():
    from genome.flow import summarize_flow
    # Each step +2 dB: adjacent similarity must not flatten the entire crescendo.
    sections=[section(i,[10**(i*.2),.1,.01],group='A') for i in range(31)]
    first=summarize_flow(sections,155)
    items=list(first['items'])
    offset=first['next_offset']
    while offset is not None:
        page=summarize_flow(sections,155,offset)
        items.extend(page['items'])
        offset=page['next_offset']
    assert len(items)>12 and len(first['items'])<=12
    assert first['ending']['end_s']==155
    assert items[0]['start_s']==0 and items[-1]['end_s']==155
    assert all(a['end_s']==b['start_s'] for a,b in zip(items,items[1:]))
    assert len({s for row in items for s in row['section_ids']})==31


def test_public_cli_validation_legacy_and_lightweight_cached_reads(measured):
    engine,g=measured
    result=packet(engine.root,'compare',g.track_id,'--a','0.371','3.713','--b','4.371','7.713')
    assert result['comparison_basis']=='exact_requested_windows'
    assert 'decreased' in invoke(engine.root,'compare',g.track_id,'--a','0.371','3.713','--b','4.371','7.713').stdout
    legacy=MusicTools(engine).compare_sections(g.track_id,g.sections[0].id,g.sections[0].id)
    assert legacy['section_a']['id']==g.sections[0].id
    for flags in [('--a','1','2'),('--a','3','2','--b','4','5'),(g.sections[0].id,g.sections[0].id,'--a','1','2','--b','3','4')]:
        assert packet(engine.root,'compare',g.track_id,*flags,code=2)['error']
    tools=MusicTools(engine)
    assert tools.get_track_digest(g.track_id)['flow']['ending']['end_s']==g.duration_s
    with pytest.raises(ValueError):
        tools.get_track_digest(g.track_id,flow_offset=-1)
    with pytest.raises(ValueError):
        tools.call('compare_sections',{'track_id':g.track_id,'range_a':[0,1,2],'range_b':[1,2]})
    script='''
import sys
from genome.engine import Engine
from genome.tools import MusicTools
t=MusicTools(Engine(sys.argv[1]))
t.get_track_digest(sys.argv[2])
t.compare_sections(sys.argv[2],range_a=[.371,3.713],range_b=[4.371,7.713])
assert not {'numpy','scipy','soundfile','matplotlib'} & set(sys.modules)
'''
    run=subprocess.run([sys.executable,'-c',script,str(engine.root),g.track_id],text=True,capture_output=True,timeout=30)
    assert run.returncode==0,run.stderr
