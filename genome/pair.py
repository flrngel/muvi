"""Paired mixture views at passage, phrase and attack scales."""

import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import soundfile as sf
from filelock import FileLock
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, resample_poly, sosfiltfilt

from genome.charts import _RENDER_LOCK
from genome.config import ANALYSIS_SR, HOP
from genome.features import stft_blocks
from genome.storage import publish_directory

VERSION = "pair-v3"
PANELS = ("passage", "phrase", "hits")
HIT_S = 0.45
DETAIL_HOP = 64
DB_RANGE = (-75, -15)


def level(g):
    return next((e.measurements.get("rms_dbfs") for e in g.evidence if e.kind == "source_metrics"), None)


def phrase_audio(directory, g, start, end):
    # Read real context around both edges for filtering and short-time windows.
    with sf.SoundFile(directory / g.artifacts["source_audio"]) as f:
        channel = None
        if g.mono_policy == "highest_energy_channel_due_to_stereo_cancellation":
            energy = sum(np.square(block).sum(axis=0) for block in f.blocks(blocksize=65536, always_2d=True))
            channel = int(np.argmax(energy))
        rate = f.samplerate
        first = max(0, math.floor((start - 0.25) * rate))
        last = min(f.frames, math.ceil((end + 0.25) * rate))
        f.seek(first)
        frames = f.read(last - first, always_2d=True)
    mono = frames.mean(axis=1) if channel is None else frames[:, channel]
    div = math.gcd(rate, ANALYSIS_SR)
    return resample_poly(mono, ANALYSIS_SR // div, rate // div), first / rate


def spectrum(audio, size, hop):
    return np.concatenate([block for _, block in stft_blocks(audio, size, hop)], axis=1)


def db(power, gain):
    return 10 * np.log10(np.maximum(power * 10 ** (gain / 10), 1e-16))


def prepare(engine, g, span, gain, bpm):
    start, end = span
    tracking = g.beat_tracking
    beats = [b.time_s for b in tracking.beats if start <= b.time_s < end] if tracking else []
    supported = (
        [b.time_s for b in tracking.beats if start <= b.time_s < end and b.support == "onset_supported"]
        if tracking
        else []
    )
    period = None
    if len(supported) >= 2 and len(beats) >= 3:
        period = float(np.median(np.diff(beats[:7])))
    tracked_bpm = 60 / period if period else None
    if bpm is not None:
        period = 60 / bpm
    detail_end = min(end, start + (6 * period if period else 3))
    if bpm is not None:
        ticks = np.arange(start, detail_end, period).tolist()
        basis = "user BPM, phase at excerpt start"
    else:
        ticks = [t for t in beats if start <= t < detail_end] if period else []
        basis = "tracker, half/double possible" if period else "pulse unresolved"
    streams = {s.band: s for s in g.rhythm.streams} if g.rhythm else {}
    attacks = {
        band: [t for t in streams[band].onset_times_s if start <= t < detail_end] if band in streams else []
        for band in ("low", "mid")
    }
    hits = [t for t in attacks["low"] if t + HIT_S <= detail_end][:3]
    arrays = engine.arrays(g.track_id, g.analysis_id)
    mask = (arrays["times_s"] >= start) & (arrays["times_s"] <= end)
    times_overview = arrays["times_s"][mask]
    group = max(1, math.ceil(len(times_overview) / 1000))
    columns = np.arange(0, len(times_overview), group)
    power_overview = np.add.reduceat(arrays["spectrogram_power"][:, mask], columns, axis=1)
    power_overview /= np.diff(np.r_[columns, len(times_overview)])
    overview_edges = np.r_[
        times_overview[columns] - HOP / (2 * ANALYSIS_SR), times_overview[-1] + HOP / (2 * ANALYSIS_SR)
    ]
    directory = engine.directory(g.track_id, g.analysis_id)
    audio, offset = phrase_audio(directory, g, start, detail_end)
    power = spectrum(audio, 2048, DETAIL_HOP)
    times = offset + np.arange(power.shape[1]) * DETAIL_HOP / ANALYSIS_SR
    freqs = np.fft.rfftfreq(2048, 1 / ANALYSIS_SR)
    filtered = sosfiltfilt(butter(3, [20, 250], fs=ANALYSIS_SR, btype="bandpass", output="sos"), audio)
    env = uniform_filter1d(filtered**2, size=round(0.012 * ANALYSIS_SR))
    hit_samples = np.arange(round(HIT_S * ANALYSIS_SR))[::22]
    envelopes = [db(env[round((t - offset) * ANALYSIS_SR) + hit_samples], gain) for t in hits]
    bands = [s for k, s in streams.items() if k in attacks]
    source = [e.id for e in g.evidence if e.kind in ("source_metrics", "spectral_texture")]
    timing = [eid for s in bands for eid in s.evidence_ids]
    legend = {
        "track_id": g.track_id,
        "analysis_id": g.analysis_id,
        "duration_s": g.duration_s,
        "passage_s": span,
        "phrase_s": [start, detail_end],
        "original_track_rms_dbfs": level(g),
        "gain_db": gain,
        "passage_frames_per_column": group,
        "mono_policy": g.mono_policy,
        "pulse": {
            "basis": basis,
            "bpm": (60 / period if period else None),
            "tracked_bpm": tracked_bpm,
            "ticks_s": ticks,
        },
        "detected_attacks_s": attacks,
        "available_attack_streams": list(k for k in attacks if k in streams),
        "hit_times_s": hits,
        "frequency_view_hit_s": hits[0] if hits else None,
        "evidence_ids": {
            "passage": source,
            "phrase": list(
                dict.fromkeys(
                    source + timing + (tracking.evidence_ids if tracking and bpm is None and ticks else [])
                )
            ),
            "hits": source + timing,
        },
    }
    return {
        "legend": legend,
        "overview": db(power_overview, gain),
        "mid_power": db(
            np.add.reduceat(arrays["band_power"][1, mask], columns)
            / np.diff(np.r_[columns, len(times_overview)]),
            gain,
        ),
        "overview_edges_s": np.clip(overview_edges, start, end),
        "overview_hz": arrays["frequency_edges_hz"],
        "power": db(power, gain),
        "times": times,
        "freqs": freqs,
        "envelopes": envelopes,
        "milliseconds": hit_samples * 1000 / ANALYSIS_SR,
    }


INK, MUTED, ACCENT = "#182926", "#495e59", "#a64119"


def draw_hits(fig, row, y):
    hits = row["legend"]["hit_times_s"]
    left = fig.add_axes([0.105, y, 0.43, 0.205])
    right = fig.add_axes([0.635, y, 0.33, 0.205])
    for ax in (left, right):
        ax.set_xlim(0, 1000 * HIT_S)
        ax.set_xlabel("Milliseconds from detected attack", fontsize=9)
    left.set_ylim(-75, 0)
    left.set_ylabel("RMS (dBFS)", fontsize=9)
    right.set_ylim(20, 250)
    right.set_ylabel("Hz", fontsize=9)
    if hits:
        for i, (time, env) in enumerate(zip(hits, row["envelopes"])):
            left.plot(
                row["milliseconds"],
                env,
                linestyle=["-", "--", ":"][i],
                lw=1.7,
                color=["#174c54", "#ae471d", "#5d4d83"][i],
                label=f"{time:.3f} s",
            )
        left.legend(loc="lower right", fontsize=8, ncol=len(hits), handlelength=1.4)
        t = row["times"]
        mask = (t >= hits[0] - 0.01) & (t <= hits[0] + HIT_S + 0.01)
        hz = row["freqs"] <= 270
        right.pcolormesh(
            (t[mask] - hits[0]) * 1000,
            row["freqs"][hz],
            row["power"][hz][:, mask],
            cmap="magma",
            vmin=DB_RANGE[0],
            vmax=DB_RANGE[1],
            shading="nearest",
        )
        right.set_title(f"First marked attack   {hits[0]:.3f} s", loc="left", fontsize=10)
    else:
        for ax in (left, right):
            ax.text(
                0.5,
                0.5,
                "No complete detected low hit",
                transform=ax.transAxes,
                ha="center",
                fontsize=10,
                color=MUTED,
            )


def draw_passage(fig, ax, row, y):
    info = row["legend"]
    start, end = info["passage_s"]
    _, stop = info["phrase_s"]
    edges = row["overview_hz"]
    ax.pcolormesh(
        row["overview_edges_s"],
        edges,
        row["overview"],
        shading="flat",
        cmap="magma",
        vmin=DB_RANGE[0],
        vmax=DB_RANGE[1],
    )
    ax.set_ylim(30, 10000)
    ax.set_yticks([50, 250, 1000, 4000], ["50", "250", "1k", "4k"])
    ax.axvspan(start, stop, facecolor="none", edgecolor="white", lw=2, zorder=4)
    rail = fig.add_axes([0.10, y + 0.226, 0.33, 0.014])
    rail.set(xlim=(0, info["duration_s"]), ylim=(0, 1))
    rail.set_facecolor("#d3dbd5")
    rail.axvspan(start, end, color=ACCENT)
    rail.set_xticks([])
    rail.set_yticks([])
    fig.text(0.10, y + 0.251, f"Display gain  {info['gain_db']:+.1f} dB", fontsize=9, color=MUTED)
    fig.text(
        0.445,
        y + 0.219,
        f"{start:g}–{end:g} s of {info['duration_s']:.1f} s     ·     F  {start:g}–{stop:.2f} s",
        fontsize=10,
        color=INK,
    )
    ax.tick_params(axis="x", labelbottom=False)
    curve = fig.add_axes([0.10, y - 0.065, 0.865, 0.057], sharex=ax, facecolor="#eef2ee")
    centers = (row["overview_edges_s"][1:] + row["overview_edges_s"][:-1]) / 2
    curve.plot(centers, row["mid_power"], color="#1b535c", lw=0.85)
    curve.set_ylim(-65, -5)
    curve.set_yticks([-50, -20])
    curve.set_ylabel("Mid dB", fontsize=8)
    curve.tick_params(axis="both", labelsize=8, length=2, pad=2)


def draw_phrase(fig, ax, row, y):
    from matplotlib.patches import Rectangle

    info = row["legend"]
    start, stop = info["phrase_s"]
    hits = info["hit_times_s"]
    t = row["times"]
    f = row["freqs"]
    use = (t >= start - 0.003) & (t <= stop + 0.003)
    hz = (f >= 235) & (f <= 4150)
    mesh = ax.pcolormesh(
        t[use],
        f[hz],
        row["power"][hz][:, use],
        shading="nearest",
        cmap="magma",
        vmin=DB_RANGE[0],
        vmax=DB_RANGE[1],
    )
    mesh.set_clip_path(Rectangle((start, 240), stop - start, 4100, transform=ax.transData))
    ax.set_ylim(250, 4000)
    ax.set_yticks([250, 500, 1000, 2000, 4000], ["250", "500", "1k", "2k", "4k"])
    for n, tick in enumerate(info["pulse"]["ticks_s"]):
        ax.axvline(tick, color="white", ls=":", lw=0.6, alpha=0.65)
        ax.text(tick, 1.04, str(n + 1), transform=ax.get_xaxis_transform(), fontsize=8)
    # Give the attack raster its own axis so marks cannot hide a spectral ridge.
    ax.tick_params(axis="x", labelbottom=False)
    raster = fig.add_axes([0.10, y - 0.065, 0.865, 0.057], sharex=ax, facecolor="#e4ebe6")
    raster.set_ylim(0, 1)
    raster.set_yticks([0.22, 0.72], ["low", "mid"], fontsize=8)
    raster.tick_params(axis="both", labelsize=8, length=2, pad=2)
    for band, height, marker in [("low", 0.22, "|"), ("mid", 0.72, ".")]:
        attack = info["detected_attacks_s"][band]
        raster.plot(
            attack,
            [height] * len(attack),
            marker,
            color=INK,
            ms=7,
        )
    raster.plot(
        hits,
        [0.22] * len(hits),
        "^",
        color=ACCENT,
        ms=5,
    )
    pulse = info["pulse"]
    rate = f"   {pulse['bpm']:.1f} BPM" if pulse["bpm"] else ""
    if pulse["basis"].startswith("user") and pulse["tracked_bpm"]:
        rate += f" (tracker {pulse['tracked_bpm']:.1f})"
    fig.text(
        0.10,
        y + 0.245,
        f"{pulse['basis']}{rate}    ·    | low   • mid   ▲ hits in H",
        fontsize=10,
        color=INK,
    )


def draw(rows, folder):
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.ticker import MaxNLocator, ScalarFormatter

    titles = {"passage": "Passage", "phrase": "Phrase", "hits": "Low attacks"}
    subtitles = {
        "passage": "Original-track position above each spectrum   ·   Box = phrase in panel F",
        "phrase": "Octave-spaced frequency axis   ·   Detected attacks below each spectrum",
        "hits": "20–250 Hz mixture energy   ·   Each trace starts at a detected low attack in F",
    }
    letters = dict(zip(PANELS, "PFH"))
    for panel in PANELS:
        fig = plt.figure(figsize=(10, 4.8), dpi=100, facecolor="#fafaf7")
        try:
            fig.text(0.025, 0.94, letters[panel], weight="bold", size=18, color=ACCENT)
            fig.text(0.073, 0.94, titles[panel], weight="bold", size=18, color=INK)
            fig.text(0.025, 0.89, subtitles[panel], size=10, color=MUTED)
            for idx, row in enumerate(rows):
                info = row["legend"]
                y = 0.535 - idx * 0.39
                tag = "AB"[idx]
                start = info["passage_s"][0]
                fig.text(0.023, y + 0.135, tag, weight="bold", size=17, color=INK)
                if panel == "hits":
                    draw_hits(fig, row, y)
                    continue
                ax = fig.add_axes([0.10, y, 0.865, 0.19])
                key = "passage_s" if panel == "passage" else "phrase_s"
                width = max(r["legend"][key][1] - r["legend"][key][0] for r in rows)
                ax.set_xlim(start, start + width)
                ax.set_ylabel("Hz", fontsize=9)
                ax.set_yscale("log")
                ax.xaxis.set_major_locator(MaxNLocator(7, min_n_ticks=3))
                fmt = ScalarFormatter(useOffset=False)
                ax.xaxis.set_major_formatter(fmt)
                if panel == "passage":
                    draw_passage(fig, ax, row, y)
                else:
                    draw_phrase(fig, ax, row, y)
                ax.tick_params(labelsize=9, pad=2)
                ax.minorticks_off()
            footer = (
                "Original-track seconds   ·   "
                if panel != "hits"
                else "Solid trace = spectrum at right   ·   "
            )
            fig.text(0.10, 0.025, footer + "Spectral power (dB)", fontsize=9, color=MUTED)
            bar = fig.add_axes([0.65, 0.031, 0.31, 0.019])
            bar.imshow(np.linspace(0, 1, 256)[None, :], cmap="magma", extent=(*DB_RANGE, 0, 1), aspect="auto")
            bar.set_yticks([])
            bar.set_xticks([-75, -55, -35, -15])
            bar.tick_params(labelsize=8, length=2, pad=0)
            fig.savefig(folder / f"{panel}.png", dpi=100)
        finally:
            plt.close(fig)


def render_pair(engine, genomes, spans, gains=None, bpms=(None, None)):
    if gains is None:
        levels = [level(g) for g in genomes]
        gains = [min(levels) - v for v in levels] if None not in levels else [0.0, 0.0]
        mode = (
            "whole-track RMS matched to quieter track" if None not in levels else "unmatched: RMS unavailable"
        )
    else:
        mode = "user-supplied display gains"
        if any(not math.isfinite(x) or abs(x) > 120 for x in gains):
            raise ValueError("Display gain must be finite and within ±120 dB")
    if any(b is not None and (not math.isfinite(b) or not 20 <= b <= 400) for b in bpms):
        raise ValueError("User tempo must be 20–400 BPM")
    for g, (start, end) in zip(genomes, spans):
        if not 0 <= start < end <= g.duration_s or end - start < 0.1 - 1e-10:
            raise ValueError("Each passage must be within its recording and span at least 0.1 seconds")
    identity = [VERSION, [(g.track_id, g.analysis_id) for g in genomes], spans, gains, mode, bpms]
    key = hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
    parent = engine.root / "pairs"
    parent.mkdir(exist_ok=True)
    folder = parent / key
    with FileLock(str(parent / f"{key}.lock"), timeout=120):
        if not folder.is_dir():
            rows = [prepare(engine, *args) for args in zip(genomes, spans, gains, bpms)]
            with TemporaryDirectory(dir=parent, prefix=".render-") as temp:
                stage = Path(temp) / "views"
                stage.mkdir()
                with _RENDER_LOCK:
                    draw(rows, stage)
                legend = {
                    "version": VERSION,
                    "alignment": "Manual excerpt starts, original seconds, no time warping. Beat numbers are local ticks.",
                    "gain_basis": mode,
                    "display_db": DB_RANGE,
                    "passage_mid_curve": {
                        "band_hz": [250, 2000],
                        "display_db": [-65, -5],
                        "reference": "window-normalized digital band power",
                    },
                    "image_pixels": [1000, 480],
                    "spectral_reference": "one-sided Hann-window digital power; passage sums log bands, details show FFT-bin power",
                    "resolution": {
                        "analysis_hz": ANALYSIS_SR,
                        "passage_fft": 2048,
                        "passage_hop": HOP,
                        "detail_fft": 2048,
                        "detail_hop": DETAIL_HOP,
                        "envelope_rms_ms": 12,
                        "envelope_filter": "forward/backward third-order Butterworth 20–250 Hz",
                    },
                    "selection": "Phrase starts at excerpt start, up to six pulses or three seconds. First three detected low attacks with 450 ms remaining in phrase. Spectrum shows first.",
                    "limitations": "Overlapping sources, pitch changes smaller than spectral resolution and exact decay can be unresolved.",
                    "tracks": dict(zip("AB", [r["legend"] for r in rows])),
                }
                (stage / "legend.json").write_text(
                    json.dumps(legend, allow_nan=False, indent=2), encoding="utf-8"
                )
                publish_directory(stage, folder)
    result = {}
    for name in (*PANELS, "legend"):
        path = folder / ("legend.json" if name == "legend" else f"{name}.png")
        result[name] = {"path": str(path), "uri": path.as_uri()}
        if name in PANELS:
            result[name]["resource_uri"] = f"muvi://pairs/{key}/{name}"
        else:
            result[name]["resource_uri"] = f"muvi://pairs/{key}/metadata/legend"
    return result
