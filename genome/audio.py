"""Lossless original retention and resource-bounded decoding."""

import hashlib
import math
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

MAX_DURATION = 600
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_DECODE_BYTES = 384 * 1024 * 1024
ANALYSIS_SR = 22050


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def decode(path: Path):
    if not path.is_file():
        raise ValueError("Audio file does not exist")
    if path.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError("Audio exceeds the 200 MiB file limit")
    try:
        info = sf.info(path)
        if not 0.1 <= info.duration <= MAX_DURATION:
            raise ValueError("Choose audio between 0.1 seconds and 10 minutes")
        if info.channels not in (1, 2):
            raise ValueError("Choose a mono or stereo recording")
        if not 8000 <= info.samplerate <= 192000:
            raise ValueError("Supported sample rates are 8–192 kHz")
        if info.frames * info.channels * 8 > MAX_DECODE_BYTES:
            raise ValueError("Decoded audio exceeds 384 MiB; choose a shorter excerpt")
        pcm, sr = sf.read(path, always_2d=True, dtype="float64")
    except (sf.LibsndfileError, RuntimeError) as exc:
        raise ValueError("Cannot decode this audio. Try WAV, FLAC, OGG, or MP3.") from exc
    if not np.all(np.isfinite(pcm)):
        raise ValueError("Audio contains non-finite samples")
    mono = pcm.mean(axis=1)
    policy = "channel_mean"
    channel_energy = np.mean(pcm**2, axis=0)
    if np.mean(mono**2) < 0.05 * np.max(channel_energy):
        mono = pcm[:, int(np.argmax(channel_energy))]
        policy = "highest_energy_channel_due_to_stereo_cancellation"
    divisor = math.gcd(sr, ANALYSIS_SR)
    analysis = resample_poly(mono, ANALYSIS_SR//divisor, sr//divisor).astype(np.float32)
    return pcm, sr, analysis, policy, info.format


def source_metrics(pcm, sr):
    peak = float(np.max(np.abs(pcm)))
    rms = float(np.sqrt(np.mean(pcm**2)))
    metrics = {"sample_peak_dbfs": float(20*np.log10(peak)) if peak > 0 else None,
               "rms_dbfs": float(20*np.log10(rms)) if rms > 0 else None,
               "crest_db": float(20*np.log10(peak/rms)) if rms > 0 else None,
               "samples_at_or_above_full_scale": float(np.sum(np.abs(pcm) >= 1)),
               "stereo_correlation": None, "side_to_total_energy": None,
               "integrated_lufs": None, "true_peak_dbtp": None,
               "measurement_sample_rate": float(sr)}
    if pcm.shape[1] == 2:
        left, right = pcm.T
        if np.std(left) > 1e-10 and np.std(right) > 1e-10:
            metrics["stereo_correlation"] = float(np.corrcoef(left, right)[0, 1])
        mid, side = (left+right)/2, (left-right)/2
        total = np.mean(mid**2 + side**2)
        metrics["side_to_total_energy"] = float(np.mean(side**2)/total) if total > 0 else None
    return metrics

