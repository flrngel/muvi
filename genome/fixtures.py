"""Original, seeded synthesis. Ground truth is only valid for these generated signals."""

from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt


def synthesize(path: Path, bpm=150.0, duration=25.6, seed=7, kind="arrangement", offset=0.2):
    sr = 22050
    rng = np.random.default_rng(seed)
    n = round(duration * sr)
    audio = np.zeros((n, 2), dtype=np.float64)
    truth = {"kind": kind, "bpm": bpm, "seed": seed, "onsets_s": [], "boundaries_s": [],
             "bass_intervals": [], "sample_rate": sr, "license": "original mathematical synthesis"}
    if kind == "silence":
        pass
    elif kind == "noise":
        audio[:] = rng.normal(0, 0.04, audio.shape)
        truth["bpm"] = None
    elif kind == "tone":
        audio[:] = (0.2 * np.sin(2 * np.pi * 220 * np.arange(n) / sr))[:, None]
        truth["bpm"] = None
    else:
        quarter = 60 / bpm
        boundaries = [duration * x / 4 for x in range(5)]
        if kind == "arrangement":
            truth["boundaries_s"] = boundaries[1:-1]
        def add(start, signal, pan=0):
            index = round(start * sr)
            if index >= n:
                return
            signal = signal[:n-index]
            audio[index:index+len(signal), 0] += signal * (1 - max(0, pan) * 0.5)
            audio[index:index+len(signal), 1] += signal * (1 + min(0, pan) * 0.5)
        for i, start in enumerate(np.arange(offset, duration - 0.15, quarter)):
            if kind == "missing" and i % 8 == 5:
                continue
            if kind == "arrangement" and boundaries[2] <= start < boundaries[3]:
                continue
            t = np.arange(round(0.24 * sr)) / sr
            kick = np.sin(2*np.pi*(48*t + 3*(1-np.exp(-t*35)))) * np.exp(-t*20)
            kick += rng.normal(0, 0.12, len(t)) * np.exp(-t*180)
            add(start, np.tanh(kick * 1.6) * 0.5)
            truth["onsets_s"].append(float(start))
        if kind in ("arrangement", "alternate_bass"):
            for i, start in enumerate(np.arange(offset + quarter/2, duration - 0.1, quarter)):
                if kind == "arrangement" and start < boundaries[1]:
                    continue
                t = np.arange(round(0.07 * sr))/sr
                noise = sosfilt(butter(3, 4500, "highpass", fs=sr, output="sos"), rng.normal(size=len(t)))
                add(start, noise*np.exp(-t*55)*0.17, pan=(-1 if i % 2 else 1)*0.65)
            for i, start in enumerate(np.arange(offset, duration-0.5, quarter*4)):
                if (kind == "alternate_bass" and i % 2) or (kind == "arrangement" and start < boundaries[1]):
                    continue
                length = min(quarter*3.5, duration-start)
                t = np.arange(round(length*sr))/sr
                bass = np.sin(2*np.pi*(55 if i % 4 < 2 else 65.406)*t)
                env = np.minimum(t/0.03, 1)*np.minimum((length-t)/0.08, 1)
                add(start, bass*env*0.15)
                truth["bass_intervals"].append([float(start), float(start+length)])
            if kind == "arrangement":
                start, length = boundaries[2], boundaries[3]-boundaries[2]
                t = np.arange(round(length*sr))/sr
                pad = sum(np.sin(2*np.pi*f*t) for f in [220, 261.626, 329.628])/3
                add(start, pad*np.minimum(t/0.1, 1)*np.minimum((length-t)/0.1, 1)*0.19)
    if kind == "antiphase":
        audio[:, 1] = -audio[:, 0]
    sf.write(path, audio, sr, subtype="FLOAT")
    return truth

