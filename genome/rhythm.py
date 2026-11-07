"""Band-specific attacks and bounded pulse evidence. No source or meter inference."""

import cmath
import math
from statistics import median

from genome.config import ANALYSIS_SR, BANDS, HOP
from genome.schema import PulseSummary, PulseWindow, Rhythm, RhythmStream


def pulse_summary(times):
    result = PulseSummary(event_count=len(times))
    if len(times) < 4:
        return result
    gaps = [b-a for a, b in zip(times, times[1:])]
    period = median(gaps)
    if period <= 0:
        return result
    # Whole-cycle gaps retain missing-event evidence without halving the pulse rate.
    cycles = [max(1, round(g/period)) for g in gaps]
    positions = [0]
    for cycle in cycles:
        positions.append(positions[-1]+cycle)
    xmean = sum(positions)/len(positions)
    ymean = sum(times)/len(times)
    denominator = sum((x-xmean)**2 for x in positions)
    # Fit all event timestamps so 256-sample hop quantization does not accumulate
    # into a false phase drift over a long, otherwise steady pulse train.
    period = sum((x-xmean)*(t-ymean) for x, t in zip(positions, times))/denominator
    tolerance = max(.015, period*.08)
    matching = sum(abs(g-n*period) <= tolerance for g, n in zip(gaps, cycles))/len(gaps)
    concentration = abs(sum(cmath.exp(2j*math.pi*(t-times[0])/period) for t in times)/len(times))
    result.interval_match_fraction = round(matching, 4)
    result.phase_concentration = round(concentration, 4)
    # Recurrence scores are descriptive, not calibrated probabilities.
    if matching >= .7 and concentration >= .65 and .1 <= period <= 2:
        result.pulse_rate_bpm = round(60/period, 3)
        result.interval_s = round(period, 6)
        result.status = 'inferred'
    return result


def long_gaps(times, minimum=2):
    return [{'start_s':a, 'end_s':b, 'duration_s':round(b-a, 6)}
            for a, b in zip(times, times[1:]) if b-a > minimum]


def extract_rhythm(features, duration, evidence):
    import numpy as np
    from scipy.ndimage import median_filter
    from scipy.signal import find_peaks

    streams = []
    for index, band in enumerate(['low', 'mid', 'high', 'all']):
        if band == 'all':
            peaks = features['onset_frames']
        else:
            raw = np.sqrt(features['attack_band_flux'][index])
            onset = np.maximum(0, raw-median_filter(raw, size=17)*.8)
            if onset.max() > 1e-7:
                onset /= onset.max()
                peaks, _ = find_peaks(onset, prominence=.075, height=.09,
                                      distance=round(.06*ANALYSIS_SR/HOP))
                peaks = peaks[features['rms'][peaks] > max(float(features['rms'].max())*.015, 1e-6)]
            else:
                peaks = np.array([], dtype=int)
            features[f'{band}_onset_frames'] = peaks
            features[f'{band}_onset_strength'] = onset
        times = [round(float(t), 6) for t in features['times_s'][peaks] if t < duration]
        pulse = pulse_summary(times)
        windows = []
        for start in np.arange(0, max(0, duration-1.999), 2):
            end = min(float(start)+4, duration)
            windows.append(PulseWindow(start_s=float(start), end_s=end,
                                       pulse=pulse_summary([t for t in times if start <= t < end])))
        rates = [w.pulse.pulse_rate_bpm for w in windows if w.pulse.pulse_rate_bpm is not None]
        varying = len(rates) >= 2 and max(rates)/min(rates) > 1.12
        status = 'varying' if varying else 'steady' if pulse.status == 'inferred' else 'irregular_or_insufficient'
        frequency = list(BANDS[index]) if band != 'all' else [20, ANALYSIS_SR//2]
        ev = evidence('rhythm_stream', 0, duration, 'band_positive_flux_and_local_interval_consistency',
                      f'{band} band spectral attacks with local interval consistency. These are not isolated sources or proven musical beats.',
                      {'frequency_range_hz': frequency, 'detected_attack_count': float(len(times)),
                       'global_pulse_rate_bpm': pulse.pulse_rate_bpm,
                       'interval_match_fraction': pulse.interval_match_fraction,
                       'phase_concentration': pulse.phase_concentration,
                       'timing_status': status},
                      {'frequency_range_hz': 'Hz', 'detected_attack_count': 'detected events',
                       'global_pulse_rate_bpm': 'acoustic pulses/min, not unique musical tempo',
                       'interval_match_fraction': 'fraction, not probability',
                       'phase_concentration': 'circular concentration, not probability', 'timing_status': 'heuristic'})
        streams.append(RhythmStream(band=band, frequency_range_hz=frequency, onset_times_s=times,
                                    pulse=pulse, local_windows=windows, timing_status=status, evidence_ids=[ev.id]))
    return Rhythm(streams=streams)
