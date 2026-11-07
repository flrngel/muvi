"""Bounded multi-resolution STFT: long windows never determine transient times."""

import numpy as np
from scipy.fft import rfft
from scipy.ndimage import median_filter, uniform_filter1d
from scipy.signal import find_peaks

from genome.audio import ANALYSIS_SR

HOP = 256
BANDS = ((20, 250), (250, 2000), (2000, 11025))
PARAMETERS = {"sample_rate": ANALYSIS_SR, "hop_length": HOP, "fft_sizes": [512, 2048, 8192],
              "max_duration_s": 600, "onset_min_gap_s": 0.06,
              "onset_prominence": 0.075, "section_min_s": 3.0,
              "object_cosine_threshold": 0.94, "max_objects": 8,
              "object_descriptor": "short_window_positive_spectral_flux",
              "section_descriptor": "band_fractions_and_log_band_power",
              "tempo_autocorrelation": "mean_centered_gaussian_lag_smoothing",
              "pattern_min_phase_coherence": 0.65,
              "feature_normalization": "one_sided_window_energy_power"}


def stft_blocks(y, nfft, hop=HOP, block_frames=192):
    padded = np.pad(y, (nfft//2, nfft//2))
    frames = np.lib.stride_tricks.sliding_window_view(padded, nfft)[::hop]
    window = np.hanning(nfft).astype(np.float32)
    norm = nfft * np.sum(window**2)
    for start in range(0, len(frames), block_frames):
        spectrum = rfft(frames[start:start+block_frames] * window, axis=1)
        power = (np.abs(spectrum)**2 * (2 / norm)).T
        power[[0, -1]] *= 0.5
        yield start, power.astype(np.float32)


def extract(y):
    count = len(y)//HOP + 1
    times = np.arange(count)*HOP/ANALYSIS_SR
    band_power = np.zeros((3, count), np.float32)
    spectrogram = np.zeros((72, count), np.float32)
    chroma = np.zeros((12, count), np.float32)
    centroid = np.zeros(count, np.float32)
    flatness = np.zeros(count, np.float32)
    rms = np.zeros(count, np.float32)
    flux = np.zeros(count, np.float32)
    attack_bands = np.zeros((3, count), np.float32)
    attack_centroid = np.zeros(count, np.float32)
    log_edges = np.geomspace(30, ANALYSIS_SR/2, 73)
    for nfft in (512, 2048, 8192):
        frequencies = np.fft.rfftfreq(nfft, 1/ANALYSIS_SR)
        previous = None
        log_indices = np.clip(np.digitize(frequencies, log_edges)-1, 0, 71)
        pitch_bins = np.where((frequencies >= 55) & (frequencies <= 4400))[0]
        pitch_classes = np.round(69+12*np.log2(frequencies[pitch_bins]/440)).astype(int) % 12
        for start, power in stft_blocks(y, nfft):
            end = start + power.shape[1]
            if nfft == 512:
                rms[start:end] = np.sqrt(power.sum(axis=0))
                magnitude = np.sqrt(power)
                prev = magnitude[:, :1] if previous is None else previous[:, None]
                delta = np.maximum(0, np.diff(np.concatenate([prev, magnitude], axis=1), axis=1))
                flux[start:end] = delta.sum(axis=0)
                for i, (lo, hi) in enumerate(BANDS):
                    attack_bands[i, start:end] = (delta[(frequencies >= lo)&(frequencies < hi)]**2).sum(axis=0)
                attack_centroid[start:end] = (delta*frequencies[:, None]).sum(axis=0)/(delta.sum(axis=0)+1e-20)
                previous = magnitude[:, -1]
            if nfft == 2048:
                total = power.sum(axis=0) + 1e-20
                centroid[start:end] = (power*frequencies[:, None]).sum(axis=0)/total
                flatness[start:end] = np.exp(np.mean(np.log(power+1e-20), axis=0))/(np.mean(power, axis=0)+1e-20)
                for i, (lo, hi) in enumerate(BANDS):
                    if i > 0:
                        band_power[i, start:end] = power[(frequencies >= lo)&(frequencies < hi)].sum(axis=0)
                for i in range(72):
                    spectrogram[i, start:end] = power[(log_indices == i)&(frequencies >= log_edges[0])].sum(axis=0)
            if nfft == 8192:
                band_power[0, start:end] = power[(frequencies >= 20)&(frequencies < 250)].sum(axis=0)
                for i in range(12):
                    chroma[i, start:end] = power[pitch_bins[pitch_classes == i]].sum(axis=0)
    # Local background suppression prevents constant textures from becoming a pulse train.
    onset = np.maximum(0, flux - median_filter(flux, size=17)*0.8)
    if onset.max() > 1e-7:
        onset /= onset.max()
        peaks, _ = find_peaks(onset, prominence=0.075, height=0.09,
                              distance=round(0.06*ANALYSIS_SR/HOP))
        peaks = peaks[rms[peaks] > max(float(rms.max())*0.015, 1e-6)]
    else:
        onset[:] = 0
        peaks = np.array([], dtype=int)
    # Median-filter masks are harmonic/percussive-like textures, never isolated sources.
    harmonic = median_filter(spectrogram, size=(1, 17))
    percussive = median_filter(spectrogram, size=(7, 1))
    harmonic_ratio = harmonic.sum(axis=0)/(harmonic.sum(axis=0)+percussive.sum(axis=0)+1e-20)
    return {"times_s": times.astype(np.float32), "band_power": band_power, "rms": rms,
            "onset_strength": onset, "onset_frames": peaks, "centroid_hz": centroid,
            "flatness": flatness, "spectrogram_power": spectrogram,
            "attack_band_flux": attack_bands, "attack_centroid_hz": attack_centroid,
            "frequency_edges_hz": log_edges, "chroma_power": chroma,
            "harmonic_like_ratio": harmonic_ratio,
            "smoothed_band_power": uniform_filter1d(band_power, size=43, axis=1)}

