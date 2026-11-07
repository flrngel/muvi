import numpy as np
from scipy.signal import correlate, find_peaks
from scipy.ndimage import gaussian_filter1d

from genome.audio import ANALYSIS_SR
from genome.features import HOP
from genome.schema import Tempo


def estimate(features, duration):
    peaks = features["onset_frames"]
    onset = features["onset_strength"]
    if len(peaks) < 4 or duration < 2:
        return Tempo()
    ac = correlate(onset, onset, mode="full", method="fft")[len(onset)-1:]
    # Integrate neighboring lags so frame quantization cannot favor a third-period alias.
    ac = gaussian_filter1d(ac, 1)
    ac /= max(float(ac[0]), 1e-12)
    frame_rate = ANALYSIS_SR/HOP
    lo, hi = round(frame_rate*60/220), min(len(ac)-1, round(frame_rate*60/55))
    candidates, _ = find_peaks(ac[lo:hi+1])
    if not len(candidates):
        return Tempo()
    lag = int(candidates[np.argmax(ac[candidates+lo])]+lo)
    score = float(ac[lag])
    if score < 0.18:
        return Tempo()
    # Parabolic interpolation reduces integer-lag tempo quantization.
    denominator = ac[lag-1] - 2*ac[lag] + ac[lag+1]
    correction = 0.5*(ac[lag-1]-ac[lag+1])/denominator if abs(denominator) > 1e-10 else 0
    bpm = 60*frame_rate/(lag+float(np.clip(correction, -0.5, 0.5)))
    values = [bpm, bpm/2, bpm*2]
    values = [round(v, 2) for v in values if 30 <= v <= 360]
    period = 60/bpm
    times = features["times_s"][peaks]
    strengths = onset[peaks]
    # Phase proposals are derived from actual onsets. No downbeat or meter assertion.
    phases = times[:min(len(times), 32)] % period
    scores = [np.sum(strengths*np.exp(-((np.minimum((times-p)%period, period-(times-p)%period))/0.04)**2))
              for p in phases]
    phase = float(phases[np.argmax(scores)])
    beats = np.arange(phase, duration, period)
    return Tempo(candidates_bpm=values, preferred_bpm=values[0],
                 candidate_scores=[round(float(ac[min(len(ac)-1, round(60*frame_rate/v))]), 4) for v in values],
                 status="inferred", beat_times_s=[round(float(t), 6) for t in beats])

