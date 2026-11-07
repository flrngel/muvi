import hashlib
import json
import threading

import numpy as np

_RENDER_LOCK = threading.Lock()


def render(engine, g, start, end):
    """A synchronized human/VLM audit image with companion numeric coordinates."""
    key = hashlib.sha256(f"{g.analysis_id}:{start:.9f}:{end:.9f}:tile-v1".encode()).hexdigest()[:20]
    relative = f"images/tile-{key}.png"
    path = engine.directory(g.track_id, g.analysis_id)/relative
    legend_path = path.with_suffix(".json")
    with _RENDER_LOCK:
        if not path.exists() or not legend_path.exists():
            import matplotlib
            matplotlib.use("Agg")
            from matplotlib import pyplot as plt
            from matplotlib.colors import LinearSegmentedColormap
            a = engine.arrays(g.track_id, g.analysis_id)
            mask = (a["times_s"] >= start)&(a["times_s"] <= end)
            if not mask.any():
                raise ValueError("Interval is too short for a visual tile; use at least 0.05 seconds")
            t = a["times_s"][mask]
            spec = a["spectrogram_power"][:, mask]
            cm = LinearSegmentedColormap.from_list("muvi", ["#101418", "#23423e", "#3d826b", "#b5ed9c", "#f9f5d7"])
            with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10, "text.color": "#e4e8df",
                                 "axes.labelcolor": "#b6beb6", "xtick.color": "#a9b3ac", "ytick.color": "#a9b3ac",
                                 "axes.edgecolor": "#3b4540", "figure.facecolor": "#101418", "axes.facecolor": "#101418"}):
                fig, axes = plt.subplots(4, 1, figsize=(16, 9), dpi=100, sharex=True,
                                         gridspec_kw={"height_ratios": [3, 1.3, 1.2, 1.5]}, layout="constrained")
                try:
                    db = 10*np.log10(spec+1e-12)
                    axes[0].pcolormesh(t, a["frequency_edges_hz"][:-1], db, shading="nearest", cmap=cm, vmin=-90, vmax=-20)
                    axes[0].set_yscale("log")
                    axes[0].set_ylim(30, 11025)
                    axes[0].set_yticks([50, 250, 1000, 4000, 10000], ["50", "250", "1k", "4k", "10k"])
                    axes[0].set_ylabel("Frequency (Hz, log)")
                    axes[0].set_title(f"{g.title}  ·  original mixture measurements\n{g.analysis_id}  |  {start:.3f}–{end:.3f} s",
                                      loc="left", color="#e4e8df", pad=14, fontsize=13)
                    colors = ["#c7f2a4", "#8db9eb", "#d3a6e7"]
                    for i, label in enumerate(["Low 20–250 Hz", "Mid 250–2k Hz", "High 2–11k Hz"]):
                        axes[1].plot(t, 10*np.log10(a["band_power"][i, mask]+1e-12), color=colors[i],
                                     label=label, linewidth=1, linestyle=["-", "--", ":"][i])
                    axes[1].set_ylabel("Band power (dB)")
                    axes[1].legend(loc="upper right", ncol=3, frameon=True, facecolor="#101418", edgecolor="none", framealpha=0.9, labelcolor="#d5dfd4", fontsize=9)
                    axes[2].plot(t, a["onset_strength"][mask], color="#dfe9d4", linewidth=0.8)
                    for beat in g.tempo.beat_times_s:
                        if start <= beat <= end:
                            axes[2].axvline(beat, color="#88b690", linestyle=":", alpha=0.3)
                    axes[2].set_ylabel("Onset strength\n(relative)")
                    for i, sound in enumerate(g.sound_objects):
                        intervals = [(max(o.start_s, start), min(o.end_s, end)-max(o.start_s, start))
                                     for o in g.occurrences if o.sound_object_id == sound.id
                                     and o.end_s > start and o.start_s < end]
                        axes[3].broken_barh(intervals, (i-0.3, 0.6), facecolors=colors[i % 3])
                    axes[3].set_yticks(range(len(g.sound_objects)), [s.id for s in g.sound_objects])
                    axes[3].set_ylabel("Acoustic objects\n(source unresolved)")
                    axes[3].set_xlabel("Original-track time (seconds) · dotted rhythm grid is provisional")
                    for section in g.sections:
                        if start < section.start_s < end:
                            for ax in axes:
                                ax.axvline(section.start_s, color="#9aa698", linestyle="--", linewidth=0.7)
                    axes[-1].set_xlim(start, end)
                    fig.savefig(path, dpi=100)
                finally:
                    plt.close(fig)
            legend = {"analysis_id": g.analysis_id, "track_id": g.track_id,
                      "time_span": {"start_s": start, "end_s": end}, "source": "original mixture; no separation",
                      "panels": ["log-frequency STFT power (2048 samples)", "multi-resolution band power (512/2048/8192)",
                                 "short-window onset strength and provisional beats", "acoustic-object occurrences"],
                      "frequency_edges_hz": a["frequency_edges_hz"].tolist(), "power_reference": "window-normalized digital power",
                      "display_db_range": [-90, -20], "raw_arrays": "arrays/features.npz",
                      "evidence_ids": [e.id for e in g.evidence if e.start_s < end and e.end_s > start],
                      "measurement_status": "observed_with_inferred_overlays"}
            legend_path.write_text(json.dumps(legend, indent=2), encoding="utf-8")
    return relative, str(legend_path.relative_to(engine.directory(g.track_id, g.analysis_id))).replace("\\", "/")

