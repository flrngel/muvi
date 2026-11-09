import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest
import soundfile as sf

from genome.engine import Engine
from genome.schema import Genome
from genome.tools import MusicTools
from tests.test_cli import invoke, packet


@pytest.fixture(scope='module')
def measured(tmp_path_factory):
    root = tmp_path_factory.mktemp('windows')
    sr = 22050
    t = np.arange(sr*12)/sr
    audio = .2*np.sin(2*np.pi*80*t)
    audio[sr*4:sr*8] = .1*np.sin(2*np.pi*800*t[sr*4:sr*8])
    audio[sr*8:] = 0
    path = root/'tones.wav'
    sf.write(path, audio, sr, subtype='PCM_24')
    engine = Engine(root/'library')
    g = engine.analyze(path)
    return engine, g, path


def test_exact_windows_energy_activity_and_retrievable_measurements(measured):
    engine, g, source = measured
    tools = MusicTools(engine)
    a = tools.get_window(g.track_id, .371, 3.713)
    b = tools.get_window(g.track_id, 4.37, 7.71)
    silence = tools.get_window(g.track_id, 8.37, 11.71)
    assert a['bands']['low']['fraction'] > .95
    assert b['bands']['mid']['fraction'] > .95
    assert a['bands']['low']['mean_power'] > b['bands']['low']['mean_power']*100
    assert b['bands']['mid']['mean_power'] > a['bands']['mid']['mean_power']*100
    assert b['source_rms_dbfs']-a['source_rms_dbfs'] == pytest.approx(-6.0206, abs=.02)
    assert silence['source_activity'] == 'digital_silence'
    assert silence['source_rms_dbfs'] is None and silence['attack_count'] == 0
    assert silence['beats']['status'] == 'unresolved'
    pcm,sr = sf.read(source)
    expected = 20*np.log10(np.sqrt(np.mean(pcm[round(.371*sr):round(3.713*sr)]**2)))
    assert a['source_rms_dbfs'] == pytest.approx(expected, abs=1e-10)
    assert a['time_span'] == dict(start_s=.371,end_s=3.713)
    ev = tools.get_evidence(g.track_id, a['evidence_ids'])['evidence']
    scoped = next(e for e in ev if e['kind']=='window_summary')
    assert scoped['start_s']==.371 and scoped['end_s']==3.713
    assert scoped['measurements']['mean_band_power'][0] == a['bands']['low']['mean_power']
    assert scoped['measurements']['source_rms_dbfs'] == expected


def test_whole_track_summary_matches_duration_weighted_equal_parts(measured):
    engine,g,_ = measured
    tools=MusicTools(engine)
    whole=tools.get_window(g.track_id)
    parts=[tools.get_window(g.track_id,i,i+4) for i in (0,4,8)]
    for band in ('low','mid','high'):
        expected=sum(p['bands'][band]['mean_power']*p['measurement_basis']['spectral_frame_count'] for p in parts)
        expected/=sum(p['measurement_basis']['spectral_frame_count'] for p in parts)
        assert whole['bands'][band]['mean_power']==pytest.approx(expected,rel=1e-10)
    assert whole['source_activity']=='signal_present'
    assert whole['attack_count']==sum(p['attack_count'] for p in parts)


def test_subframe_interval_does_not_invent_spectral_silence(measured):
    engine,g,_=measured
    window=MusicTools(engine).get_window(g.track_id, .001, .002)
    assert window['measurement_basis']['spectral_frame_count']==0
    assert window['source_activity']=='signal_present'
    assert all(v['mean_power'] is None for v in window['bands'].values())


def test_concurrent_query_cache_and_unknown_evidence(measured):
    engine,g,_=measured
    tools=MusicTools(engine)
    with ThreadPoolExecutor(max_workers=3) as pool:
        records=list(pool.map(lambda _:tools.get_window(g.track_id,1.23,2.34),range(3)))
    assert records[0]==records[1]==records[2]
    with pytest.raises(KeyError):
        tools.get_evidence(g.track_id,['W'+'0'*20])
    with pytest.raises(KeyError):
        tools.get_evidence(g.track_id,['W../../genome'])


def test_cli_and_cached_window_evidence_stay_lightweight(measured):
    engine,g,_=measured
    result=packet(engine.root,'window',g.track_id,'--start',.371,'--end',3.713)
    assert result['time_span']['start_s']==.371
    assert 'WINDOW' in invoke(engine.root,'window',g.track_id).stdout
    assert packet(engine.root,'window',g.track_id,'--end',20,code=2)['error']
    script='''
import sys
from genome.engine import Engine
from genome.tools import MusicTools
t=MusicTools(Engine(sys.argv[1]))
p=t.get_window(sys.argv[2],.371,3.713)
t.get_evidence(sys.argv[2],p['evidence_ids'])
assert not {'numpy','scipy','soundfile','matplotlib'} & set(sys.modules)
'''
    process=subprocess.run([sys.executable,'-c',script,str(engine.root),g.track_id],capture_output=True,text=True,timeout=30)
    assert process.returncode==0,process.stderr


def test_legacy_analysis_and_digest_section_pagination(measured):
    engine,g,_=measured
    data=g.model_dump()
    data['schema_version']='0.1.0'
    data.pop('rhythm')
    data.pop('beat_tracking')
    prototype=data['sections'][0]
    data['sections']=[{**prototype,'id':f'SEC_{i:02}','start_s':i*.4,'end_s':(i+1)*.4} for i in range(30)]
    legacy=Genome.model_validate(data)
    class Cached:
        def load(self,_): return legacy
        def directory(self,*args): return engine.directory(*args)
        def arrays(self,*args): return engine.arrays(*args)
    tools=MusicTools(Cached())
    first=tools.get_track_digest(g.track_id)
    last=tools.get_track_digest(g.track_id,first['next_section_offset'])
    assert len(first['sections'])==24 and len(last['sections'])==6
    assert last['sections'][-1]['end_s']==g.duration_s and last['next_section_offset'] is None
    assert 'SEC_29' in last['digest_text']
    window=tools.get_window(g.track_id,.371,3.713)
    assert not window['beats']['available'] and window['band_attacks']=={}
    with pytest.raises(ValueError):
        tools.get_track_digest(g.track_id,-1)
    assert json.dumps(window,allow_nan=False)
