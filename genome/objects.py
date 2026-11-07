import numpy as np

from genome.schema import Occurrence, Pattern, SoundObject, Span


def index_objects(features, duration, evidence):
    times, power = features["times_s"], features["band_power"]
    peaks = features["onset_frames"]
    clusters = []
    occurrences = []
    for frame in peaks:
        end_frame = min(frame+9, len(times))
        bands = power[:, frame:end_frame].mean(axis=1)
        ratios = bands/(bands.sum()+1e-15)
        centroid = float(features["centroid_hz"][frame:end_frame].mean())
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
                      "onset_descriptor_cosine_clustering", "Recurring mixture descriptors; not an isolated instrument.",
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
            matches = np.abs(gaps-interval) < max(0.04, interval*0.08)
            if interval > 0.05 and matches.mean() >= 0.65:
                exceptions = [float(t+interval*j) for t, gap in zip(ts[:-1], gaps)
                              if gap > interval*1.5 for j in range(1, min(128, round(gap/interval)))]
                pev = evidence("recurrence", float(ts[0]), min(duration, float(ts[-1])+0.16),
                               "inter_onset_interval_consistency", "Acoustic-object events recur at a provisional interval.",
                               {"interval_s": interval, "matching_gap_fraction": float(matches.mean()),
                                "exceptions_s": exceptions}, {"interval_s": "s", "matching_gap_fraction": "fraction, not probability",
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
    return objects, occurrences, patterns

