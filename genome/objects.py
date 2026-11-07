import numpy as np

from genome.schema import Occurrence, Pattern, SoundObject, Span


def index_objects(features, duration, evidence):
    times = features["times_s"]
    peaks = features["onset_frames"]
    clusters = []
    occurrences = []
    for frame in peaks:
        end_frame = min(frame+3, len(times))
        # Incremental short-window energy distinguishes an entering bright attack from a sustained bass.
        bands = features["attack_band_flux"][:, max(0, frame-1):end_frame].sum(axis=1)
        ratios = bands/(bands.sum()+1e-15)
        centroid = float(features["attack_centroid_hz"][frame:end_frame].mean())
        flatness = float(features["flatness"][frame:end_frame].mean())
        descriptor = np.r_[ratios, np.log1p(centroid)/10*0.3, flatness*0.4]
        descriptor /= max(np.linalg.norm(descriptor), 1e-12)
        sims = [float(np.dot(descriptor, c["descriptor"])) for c in clusters]
        if sims and max(sims) >= 0.94:
            cluster = int(np.argmax(sims))
            similarity = float(np.clip(sims[cluster], 0, 1))
        elif len(clusters) < 8:
            cluster, similarity = len(clusters), 1.0
            clusters.append({"descriptor": descriptor, "ratios": ratios, "centroid": centroid,
                             "flatness": flatness, "frame": frame, "times": []})
        else:
            # Leave weak/unmatched events unassigned rather than forcing source identity.
            continue
        start = float(times[frame])
        if start >= duration:
            continue
        clusters[cluster]["times"].append(start)
        occurrences.append(Occurrence(id=f"O{len(occurrences)+1:05}", sound_object_id=f"S{cluster+1:02}",
                                      start_s=start, end_s=min(duration, start+0.16), similarity=similarity))
    objects, patterns = [], []
    for index, c in enumerate(clusters):
        sid = f"S{index+1:02}"
        ts = np.array(c["times"])
        band = int(np.argmax(c["ratios"]))
        name = ["Low pulse", "Midrange attack", "Bright pulse"][band]
        role = ["low-pulse", "midrange-transient", "subdivision"][band]
        ev = evidence("acoustic_object", float(ts[0]), min(duration, float(ts[-1])+0.16),
                      "short_flux_descriptor_cosine_clustering", "Recurring spectral-change descriptors; not an isolated instrument.",
                      {"mean_band_fraction": c["ratios"].tolist(), "centroid_hz": c["centroid"],
                       "spectral_flatness": c["flatness"], "occurrence_count": float(len(ts))},
                      {"mean_band_fraction": "fraction within analysis bands", "centroid_hz": "Hz",
                       "spectral_flatness": "ratio", "occurrence_count": "events"})
        sound = SoundObject(id=sid, name=name, form="transient", function_candidates=[role],
                            fingerprint={"centroid_hz": c["centroid"], "spectral_flatness": c["flatness"],
                                         "low_fraction": float(c["ratios"][0]), "high_fraction": float(c["ratios"][2])},
                            prototype_crop=Span(start_s=max(0, float(ts[0])-0.04),
                                                end_s=min(duration, float(ts[0])+0.5)),
                            evidence_ids=[ev.id], occurrence_count=len(ts))
        if len(ts) >= 4:
            gaps = np.diff(ts)
            interval = float(np.median(gaps))
            cycles = np.r_[0, np.cumsum(np.maximum(1, np.round(gaps/max(interval, 1e-6))))]
            interval = float(np.polyfit(cycles, ts, 1)[0])
            phase_coherence = float(np.abs(np.exp(2j*np.pi*ts/max(interval, 1e-6)).mean()))
            matches = np.abs(gaps-interval) < max(0.04, interval*0.08)
            if interval > 0.05 and matches.mean() >= 0.65 and phase_coherence >= 0.65:
                exceptions = [float(t+interval*j) for t, gap in zip(ts[:-1], gaps)
                              if gap > interval*1.5 for j in range(1, min(128, round(gap/interval)))]
                exceptions += [float(ts[i+1]) for i, match in enumerate(matches) if not match]
                exceptions = sorted(set(exceptions))
                pev = evidence("recurrence", float(ts[0]), min(duration, float(ts[-1])+0.16),
                               "inter_onset_interval_consistency", "Acoustic-object events recur at a provisional interval; exceptions include missing expected times and observed irregular-gap endpoints.",
                               {"interval_s": interval, "matching_gap_fraction": float(matches.mean()),
                                "phase_coherence": phase_coherence,
                                "exceptions_s": exceptions}, {"interval_s": "s", "matching_gap_fraction": "fraction, not probability",
                                                           "phase_coherence": "circular concentration, not probability",
                                                           "exceptions_s": "original-track seconds"})
                pattern = Pattern(id=f"P{len(patterns)+1:02}", sound_object_id=sid, interval_s=interval,
                                  repeat_intervals=[Span(start_s=float(ts[0]), end_s=min(duration, float(ts[-1])+0.16))],
                                  repeat_count=len(ts), exceptions_s=exceptions, evidence_ids=[pev.id])
                patterns.append(pattern)
                sound.occurrence_pattern_ids.append(pattern.id)
        objects.append(sound)
    low = features["smoothed_band_power"][0]
    active = low > max(float(low.max())*0.23, 1e-7)
    changes = np.diff(np.r_[False, active, False].astype(int))
    starts, ends = np.where(changes == 1)[0], np.where(changes == -1)[0]
    intervals = [(float(times[a]), min(duration, float(times[min(b, len(times)-1)])))
                 for a, b in zip(starts, ends)]
    intervals = [(a, b) for a, b in intervals if b-a >= 0.45]
    if intervals:
        sid = f"S{len(objects)+1:02}"
        ev = evidence("low_sustain", intervals[0][0], intervals[-1][1], "low_band_activity_runs",
                      "Low-band energy persists. A pulse tail and an independent layer remain possible.",
                      {"active_duration_s": sum(b-a for a, b in intervals), "threshold_power": float(max(low.max()*0.23, 1e-7))},
                      {"active_duration_s": "s", "threshold_power": "window-normalized power"})
        objects.append(SoundObject(id=sid, name="Low sustained texture", form="noisy_or_pitched_sustained",
                                   function_candidates=["sub-foundation", "pulse-tail"],
                                   source_candidates=["independent_bass", "reverberant_or_distorted_pulse_tail"],
                                   fingerprint={"low_fraction": 1.0},
                                   prototype_crop=Span(start_s=intervals[0][0], end_s=min(intervals[0][1], intervals[0][0]+3)),
                                   evidence_ids=[ev.id], occurrence_count=len(intervals)))
        for start, end in intervals:
            occurrences.append(Occurrence(id=f"O{len(occurrences)+1:05}", sound_object_id=sid,
                                          start_s=start, end_s=end, similarity=1,
                                          similarity_type="band_threshold_membership_not_probability"))
        onset = features["onset_strength"]
        coupling = float(np.corrcoef(onset, low)[0, 1]) if np.std(onset) > 1e-10 and np.std(low) > 1e-10 else None
        relation = evidence("envelope_relationship", 0, duration, "low_band_onset_envelope_pearson",
                            "Envelope correlation measures temporal co-activity; neither correlation nor persistence identifies an independent source.",
                            {"onset_low_envelope_correlation": coupling,
                             "low_active_fraction": float(active.mean())},
                            {"onset_low_envelope_correlation": "Pearson r, not probability",
                             "low_active_fraction": "fraction of analysis frames"})
        objects[-1].evidence_ids.append(relation.id)
    return objects, occurrences, patterns

