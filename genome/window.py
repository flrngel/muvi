"""Versioned, query-scoped summaries of existing measurements; no new extraction."""

import hashlib
import json
import re

from genome.schema import Evidence

METHOD = 'cached_window_summary_v1'


def evidence_path(engine, g, identifier):
    if not re.fullmatch(r'W[0-9a-f]{20}', identifier):
        raise KeyError('Unknown evidence ID; no evidence was invented')
    return engine.directory(g.track_id, g.analysis_id)/'windows'/f'{identifier}.json'


def summarize(engine, g, start, end, metrics_provider):
    identifier = 'W'+hashlib.sha256(f'{METHOD}:{start.hex()}:{end.hex()}'.encode()).hexdigest()[:20]
    path = evidence_path(engine, g, identifier)
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    metrics = metrics_provider()['measurements']
    import numpy as np

    arrays = engine.arrays(g.track_id, g.analysis_id)
    times = arrays['times_s']
    mask = (times >= start) & (times < end)
    frames = np.flatnonzero(mask)
    count = len(frames)
    bands = arrays['band_power'][:, mask].astype(np.float64)
    mean = bands.mean(axis=1) if count else None
    total = float(mean.sum()) if count else 0
    weights = bands.sum(axis=0)
    def weighted(key):
        return float(np.average(arrays[key][mask], weights=weights)) if weights.sum() > 0 else None
    attacks = arrays['times_s'][arrays['onset_frames']]
    n_attacks = int(np.sum((attacks >= start) & (attacks < end)))
    values = {'mean_band_power': mean.tolist() if count else [],
              'source_rms_dbfs': metrics['rms_dbfs'], 'source_sample_peak_dbfs': metrics['sample_peak_dbfs'],
              'source_activity': 'digital_silence' if metrics['sample_peak_dbfs'] is None else 'signal_present',
              'energy_weighted_centroid_hz': weighted('centroid_hz'),
              'energy_weighted_harmonic_like_ratio': weighted('harmonic_like_ratio'),
              'detected_attack_count': float(n_attacks), 'attack_density_per_s': n_attacks/(end-start),
              'analysis_frame_count': float(count)}
    ev = Evidence(id=identifier, kind='window_summary', start_s=start, end_s=end, method=METHOD,
                  method_version='1', parameters_ref=g.parameters_sha256,
                  observation='Exact requested interval; spectral statistics select cached frame centers in [start,end). Source levels use original PCM sample bounds.',
                  measurements=values,
                  units={'mean_band_power':'window-normalized digital power, low/mid/high; [] means no frame',
                         'source_rms_dbfs':'dBFS; null means all source samples zero',
                         'source_sample_peak_dbfs':'dBFS; null means all source samples zero',
                         'source_activity':'digital_silence or signal_present; not perceptual audibility',
                         'energy_weighted_centroid_hz':'Hz; mixture brightness, not instrument identity',
                         'energy_weighted_harmonic_like_ratio':'texture ratio, not probability or isolated source',
                         'detected_attack_count':'events, not musical beats', 'attack_density_per_s':'events/s',
                         'analysis_frame_count':'frame centers'})
    names = ('low', 'mid', 'high')
    summary = {'source_activity': values['source_activity'],
               'source_rms_dbfs': metrics['rms_dbfs'], 'source_sample_peak_dbfs': metrics['sample_peak_dbfs'],
               'bands': {name: {'mean_power': float(mean[i]) if count else None,
                                'fraction': float(mean[i]/total) if total > 0 else None,
                                'power_db': float(10*np.log10(mean[i])) if count and mean[i] > 0 else None}
                         for i, name in enumerate(names)},
               'energy_weighted_centroid_hz': values['energy_weighted_centroid_hz'],
               'harmonic_like_ratio': values['energy_weighted_harmonic_like_ratio'],
               'attack_count': n_attacks, 'attack_density_per_s': values['attack_density_per_s'],
               'measurement_basis': {'method': METHOD, 'spectral_frame_count': count,
                                     'first_frame_s': float(times[frames[0]]) if count else None,
                                     'last_frame_s': float(times[frames[-1]]) if count else None,
                                     'source_first_sample': round(start*g.sample_rate),
                                     'source_end_sample_exclusive': round(end*g.sample_rate),
                                     'source_sample_rate': g.sample_rate,
                                     'spectral_scope': 'Cached frame centers in [start,end); STFT context extends up to 0.186s beyond a center. Bands cover 20–11025 Hz.'},
               'limitations': ['Power fraction is relative balance, not absolute energy or perceived loudness.',
                              'No frame means unavailable spectral statistics, not silence.',
                              'Brightness and harmonic-like texture do not identify instruments, vocals, genre, mood, key or chord.']}
    record = {'track_id': g.track_id, 'analysis_id': g.analysis_id,
              'summary': summary, 'evidence': ev.model_dump()}
    from genome.exports import write
    try:
        write(path, (json.dumps(record, ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8'))
    except FileExistsError:
        # Identical immutable query: another reader may have published it first.
        pass
    return record
