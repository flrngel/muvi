"""Mixture beat hypotheses from continuous novelty and a timing-constrained path.

Concepts: Ellis (2007) dynamic programming and Fourier/autocorrelation tempograms.
This independent implementation keeps attack events, beat hypotheses and support
labels separate. Numerical imports occur only during extraction, never cache reads.
"""

import math
from statistics import median

from genome.config import ANALYSIS_SR, HOP
from genome.schema import BeatCandidate, BeatTempoWindow, BeatTracking, TrackedBeat

FPS = ANALYSIS_SR / HOP


def _candidates(envelope):
    import numpy as np
    from scipy.ndimage import gaussian_filter1d
    from scipy.signal import correlate, find_peaks

    if len(envelope) < 4*FPS or float(np.max(envelope)) < 1e-6:
        return []
    x = envelope - np.mean(envelope)
    ac = correlate(x, x, mode="full", method="fft")[len(x)-1:]
    ac = gaussian_filter1d(ac, .7)
    ac /= max(float(ac[0]), 1e-12)
    nfft = 2**int(np.ceil(np.log2(len(x)*4)))
    spectrum = gaussian_filter1d(np.abs(np.fft.rfft(x*np.hanning(len(x)), nfft)), 1)
    frequencies = np.fft.rfftfreq(nfft, 1/FPS)*60
    spectrum /= max(float(spectrum.max()), 1e-12)
    peaks, _ = find_peaks(ac)
    candidates = []
    for lag in peaks:
        if not 40 <= 60*FPS/lag <= 240 or ac[lag] < .12:
            continue
        denominator = ac[lag-1] - 2*ac[lag] + ac[lag+1]
        correction = .5*(ac[lag-1]-ac[lag+1])/denominator if abs(denominator) > 1e-9 else 0
        bpm = 60*FPS/(lag+np.clip(correction, -.5, .5))
        indices = np.flatnonzero((frequencies >= bpm*.975) & (frequencies <= bpm*1.025))
        if not len(indices):
            continue
        # Fourier evidence rejects non-octave autocorrelation aliases. A second
        # harmonic allows a strong subdivision without equating it with tempo.
        support = spectrum[indices] + .5*np.interp(2*frequencies[indices], frequencies, spectrum)
        index = indices[np.argmax(support)]
        refined = float(frequencies[index])
        spectral_support = float(spectrum[index] + .5*np.interp(2*refined, frequencies, spectrum))
        prior = math.exp(-.5*(math.log2(refined/120)/.6)**2)
        score = float(ac[lag])*math.sqrt(spectral_support)*prior
        if score >= .05 and spectral_support >= .1:
            candidates.append(BeatCandidate(bpm=round(refined, 3), score=round(score, 5),
                                             autocorrelation=round(float(ac[lag]), 5),
                                             spectral_support=round(spectral_support, 5)))
    candidates.sort(key=lambda c: c.score, reverse=True)
    unique = []
    for candidate in candidates:
        if all(abs(math.log2(candidate.bpm/c.bpm)) > .04 for c in unique):
            unique.append(candidate)
    return unique[:4]


def extract_beats(features, duration, evidence):
    import numpy as np
    from scipy.ndimage import gaussian_filter1d, median_filter
    from scipy.signal import find_peaks

    bands = np.sqrt(features['attack_band_flux'])
    bands = np.maximum(0, bands-median_filter(bands, size=(1, 17))*.8)
    bands /= np.maximum(np.max(bands, axis=1, keepdims=True), 1e-8)
    onset = .5*features['onset_strength'] + .5*bands.mean(axis=0)
    candidates = _candidates(onset)
    local_observations = []
    for start in np.arange(0, max(.001, duration-3.999), 2):
        end = min(float(start)+8, duration)
        local = _candidates(onset[round(start*FPS):round(end*FPS)])
        local_observations.append((float(start), end, local))
    # A drifting performance can have strong local periodicity but no global peak.
    # Require multiple coherent local observations before using their tempo anchor.
    local_best = [local[0] for _, _, local in local_observations if local]
    if not candidates and len(local_best) >= 3 and len(local_best)/len(local_observations) >= .6:
        changes = [abs(math.log2(b.bpm/a.bpm)) for a, b in zip(local_best, local_best[1:])]
        if max(changes) < math.log2(1.25):
            candidates = [sorted(local_best, key=lambda c: c.bpm)[len(local_best)//2]]
    tracking = BeatTracking(candidates=candidates)
    if candidates:
        global_bpm = candidates[0].bpm
        centers, rates, windows = [], [], []
        for start, end, local in local_observations:
            bpm, basis = global_bpm, 'track_context'
            if local:
                # Preserve the chosen metrical level when local instrumentation
                # emphasizes half/double time. This is an explicit prior, not truth.
                selected = local[0].bpm
                if not .6*global_bpm <= selected <= 1.6*global_bpm:
                    selected *= 2**round(math.log2(global_bpm/selected))
                if .6*global_bpm <= selected <= 1.6*global_bpm:
                    bpm, basis = selected, 'local_evidence'
            centers.append((start+end)/2)
            rates.append(bpm)
            windows.append(BeatTempoWindow(start_s=float(start), end_s=end,
                                            bpm=round(bpm, 3), basis=basis))
        rates = median_filter(np.array(rates), size=3, mode='nearest')
        for window, rate in zip(windows, rates):
            window.bpm = round(float(rate), 3)
        periods = FPS*60/np.interp(np.arange(len(onset))/FPS, centers, rates)
        local_score = gaussian_filter1d(onset/max(float(np.std(onset)), 1e-8),
                                        max(.5, FPS*60/global_bpm/32))
        local_score /= max(float(np.std(local_score)), 1e-8)
        cumulative = np.zeros(len(onset))
        backlink = np.full(len(onset), -1, dtype=int)
        transitions = {}
        for index, period in enumerate(periods):
            key = round(float(period), 1)
            if key not in transitions:
                offsets = np.arange(max(1, int(.5*key)), int(2*key)+1)
                transitions[key] = (offsets, -30*np.log(offsets/key)**2)
            offsets, penalty = transitions[key]
            valid = offsets <= index
            if not np.any(valid):
                cumulative[index] = local_score[index]
                continue
            predecessors = index-offsets[valid]
            scores = cumulative[predecessors]+penalty[valid]
            best = int(np.argmax(scores))
            cumulative[index] = local_score[index]+max(0, scores[best])
            if scores[best] > 0:
                backlink[index] = predecessors[best]
        cursor = int(np.argmax(cumulative))
        frames = []
        while cursor >= 0:
            frames.append(cursor)
            cursor = int(backlink[cursor])
        frames.reverse()
        salient, _ = find_peaks(onset, height=.04, prominence=.025)
        events = []
        for frame in frames:
            nearby = salient[np.abs(salient-frame) <= round(.05*FPS)]
            supported = bool(len(nearby))
            if supported:
                frame = int(nearby[np.argmax(onset[nearby])])
            t = round(float(features['times_s'][frame]), 6)
            if t < duration and (not events or t > events[-1].time_s):
                events.append(TrackedBeat(time_s=t, onset_strength=round(float(onset[frame]), 5),
                                          support='onset_supported' if supported else 'interpolated'))
        supported_indices = [i for i, event in enumerate(events) if event.support == 'onset_supported']
        if len(supported_indices) >= 4:
            events = events[supported_indices[0]:supported_indices[-1]+1]
            if sum(e.support == 'onset_supported' for e in events)/len(events) >= .35:
                tracking.status = 'inferred'
                tracking.beats = events
                tracking.tempo_windows = windows
        features['tracked_beat_frames'] = np.array([round(e.time_s*FPS) for e in tracking.beats], dtype=np.int64)
    count = len(tracking.beats)
    supported = sum(b.support == 'onset_supported' for b in tracking.beats)
    ev = evidence('beat_tracking', 0, duration, tracking.method,
                  'Weighted mixture novelty and timing constraints produce beat hypotheses, with explicit onset support.',
                  {'preferred_bpm': candidates[0].bpm if candidates else None,
                   'candidate_bpms': [c.bpm for c in candidates], 'tracked_beat_count': float(count),
                   'onset_supported_count': float(supported), 'status': tracking.status},
                  {'preferred_bpm': 'hypothesized beats/min', 'candidate_bpms': 'hypothesized beats/min',
                   'tracked_beat_count': 'hypotheses', 'onset_supported_count': 'hypotheses near salient onsets, not correct beats',
                   'status': 'inference availability, not accuracy'})
    tracking.evidence_ids = [ev.id]
    return tracking


def summarize_beats(beats):
    """Pure-Python summary for bounded cached tool reads; never claims calibration."""
    supported = sum(b.support == 'onset_supported' for b in beats)
    fraction = supported/len(beats) if beats else 0
    gaps = [b.time_s-a.time_s for a, b in zip(beats, beats[1:])]
    interval = median(gaps) if gaps else None
    # A regular-looking extrapolation through a break must not earn a local tempo.
    inferred = len(beats) >= 4 and fraction >= .5
    return {'status': 'inferred' if inferred else 'unresolved',
            'local_tempo_bpm': round(60/interval, 3) if inferred else None,
            'beat_count': len(beats), 'onset_supported_count': supported,
            'onset_supported_fraction': round(fraction, 4),
            'tempo_basis': 'tracked_intervals_with_track_context',
            'support_warning': 'Onset proximity is supporting acoustic evidence, not proof of a correct musical beat.'}
