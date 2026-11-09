import hashlib
import json
import threading

import numpy as np

_RENDER_LOCK = threading.Lock()
RENDER_VERSION = 'tile-v2'


def overlays(g, start, end):
    tracking = g.beat_tracking
    beats = [{'time_s': b.time_s, 'support': b.support} for b in tracking.beats
             if start <= b.time_s < end] if tracking else []
    show = end-start <= 30 and len(beats) <= 64
    if tracking is None:
        caption = 'Tracked beats unavailable in this analysis; no timing grid drawn'
    elif not beats:
        caption = 'No tracked beat hypotheses in this interval'
    elif not show:
        caption = f'{len(beats)} tracked beat markers omitted at this scale; zoom for timing'
    else:
        caption = 'Tracked beat hypotheses; onset support does not establish correctness'
    boundaries = [s.start_s for s in g.sections if start < s.start_s < end]
    return ({'basis': 'stored_beat_tracking', 'status': tracking.status if tracking else 'unavailable',
             'beats': beats, 'displayed_count': len(beats) if show else 0, 'caption': caption,
             'display_limits': {'maximum_span_s': 30, 'maximum_markers': 64},
             'styles': {'onset_supported': 'solid green', 'interpolated': 'dashed amber'}},
            {'times_s': boundaries, 'displayed_count': len(boundaries) if len(boundaries) <= 24 else 0,
             'maximum_markers': 24, 'style': 'dashed lines in the acoustic-object panel only'})


def render(engine, g, start, end):
    """A synchronized human/VLM audit image with companion numeric coordinates."""
    key = hashlib.sha256(f"{g.analysis_id}:{start:.9f}:{end:.9f}:{RENDER_VERSION}".encode()).hexdigest()[:20]
    relative = f"images/tile-{key}.png"
    path = engine.directory(g.track_id, g.analysis_id)/relative
    legend_path = path.with_suffix(".json")
    with _RENDER_LOCK:
        if not path.exists() or not legend_path.exists():
            import matplotlib
            matplotlib.use("Agg")
            from matplotlib import pyplot as plt
            from matplotlib.colors import LinearSegmentedColormap
            from genome.terminal import clean
            from textwrap import fill
            beat_overlay, section_overlay = overlays(g, start, end)
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
                fig = plt.figure(figsize=(16, 9), dpi=100, layout='constrained')
                grid = fig.add_gridspec(4, 2, width_ratios=[1, .018], height_ratios=[3, 1.3, 1.2, 1.7])
                axes = [fig.add_subplot(grid[0, 0])]
                axes.extend(fig.add_subplot(grid[i, 0], sharex=axes[0]) for i in range(1, 4))
                color_axis = fig.add_subplot(grid[0, 1])
                try:
                    db = 10*np.log10(spec+1e-12)
                    mesh = axes[0].pcolormesh(t, a["frequency_edges_hz"][:-1], db, shading="nearest", cmap=cm, vmin=-90, vmax=-20)
                    fig.colorbar(mesh, cax=color_axis, label='Digital power (dB)', ticks=[-90, -70, -50, -30, -20])
                    axes[0].set_yscale("log")
                    axes[0].set_ylim(30, 11025)
                    axes[0].set_yticks([50, 250, 1000, 4000, 10000], ["50", "250", "1k", "4k", "10k"])
                    axes[0].set_ylabel("Frequency (Hz, log)")
                    axes[0].set_title(f"{fill(clean(g.title), 100)}  ·  original mixture measurements\n{g.analysis_id}  |  {start:.3f}–{end:.3f} s",
                                      loc="left", color="#e4e8df", pad=14, fontsize=13)
                    colors = ["#c7f2a4", "#8db9eb", "#d3a6e7"]
                    for i, label in enumerate(["Low 20–250 Hz", "Mid 250–2k Hz", "High 2–11k Hz"]):
                        axes[1].plot(t, 10*np.log10(a["band_power"][i, mask]+1e-12), color=colors[i],
                                     label=label, linewidth=1, linestyle=["-", "--", ":"][i])
                    axes[1].set_ylabel("Band power (dB)")
                    axes[1].legend(loc="upper right", ncol=3, frameon=True, facecolor="#101418", edgecolor="none", framealpha=0.9, labelcolor="#d5dfd4", fontsize=9)
                    axes[2].plot(t, a["onset_strength"][mask], color="#dfe9d4", linewidth=0.8)
                    if beat_overlay['displayed_count']:
                        for support, label, color, style in [('onset_supported', 'Onset-supported', '#a6d8b3', '-'),
                                                             ('interpolated', 'Interpolated', '#edbc76', '--')]:
                            times = [b['time_s'] for b in beat_overlay['beats'] if b['support'] == support]
                            if times:
                                axes[2].vlines(times, .82, 1, transform=axes[2].get_xaxis_transform(),
                                               color=color, linestyle=style, linewidth=1.2, label=label)
                        axes[2].legend(loc='lower right', bbox_to_anchor=(1, 1.02), ncol=2,
                                       frameon=False, labelcolor='#d5dfd4', fontsize=8)
                    axes[2].set_title(beat_overlay['caption'], loc='left', fontsize=9, color='#b6beb6', pad=4)
                    axes[2].set_ylabel("Onset strength\n(relative)")
                    for i, sound in enumerate(g.sound_objects):
                        intervals = [(max(o.start_s, start), min(o.end_s, end)-max(o.start_s, start))
                                     for o in g.occurrences if o.sound_object_id == sound.id
                                     and o.end_s > start and o.start_s < end]
                        axes[3].broken_barh(intervals, (i-0.3, 0.6), facecolors=colors[i % 3])
                    axes[3].set_yticks(range(len(g.sound_objects)),
                                      [fill(clean(f'{s.id}  {s.name}'), 28) for s in g.sound_objects], fontsize=8)
                    axes[3].set_title('Acoustic objects; source identity unresolved', loc='left', fontsize=9, color='#b6beb6', pad=4)
                    boundary_note = ('dashed: candidate boundaries' if section_overlay['displayed_count'] else
                                     f"{len(section_overlay['times_s'])} candidate boundaries omitted" if section_overlay['times_s'] else
                                     'no candidate boundaries in this interval')
                    axes[3].set_xlabel(f'Original-track time (seconds) | {boundary_note} | power floor -120 dB')
                    if section_overlay['displayed_count']:
                        for boundary in section_overlay['times_s']:
                            axes[3].axvline(boundary, color='#9aa698', linestyle='--', linewidth=.7, alpha=.6)
                    for ax in axes[:-1]:
                        ax.tick_params(labelbottom=False)
                    axes[-1].set_xlim(start, end)
                    fig.savefig(path, dpi=100)
                finally:
                    plt.close(fig)
            legend = {"analysis_id": g.analysis_id, "track_id": g.track_id,
                      "time_span": {"start_s": start, "end_s": end}, "source": "original mixture; no separation",
                      "panels": ["log-frequency STFT power (2048 samples)", "multi-resolution band power (512/2048/8192)",
                                 "short-window onset strength and tracked beat hypotheses", "acoustic-object occurrences"],
                      'render_version': RENDER_VERSION, 'beat_overlay': beat_overlay, 'section_overlay': section_overlay,
                      'object_labels': {s.id: s.name for s in g.sound_objects}, 'power_display_floor_db': -120,
                      "frequency_edges_hz": a["frequency_edges_hz"].tolist(), "power_reference": "window-normalized digital power",
                      "display_db_range": [-90, -20], "raw_arrays": "arrays/features.npz",
                      "evidence_ids": [e.id for e in g.evidence if e.start_s < end and e.end_s > start],
                      "measurement_status": "observed_with_inferred_overlays"}
            legend_path.write_text(json.dumps(legend, indent=2), encoding="utf-8")
    return relative, str(legend_path.relative_to(engine.directory(g.track_id, g.analysis_id))).replace("\\", "/")

