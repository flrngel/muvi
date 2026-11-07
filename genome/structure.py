import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks

from genome.audio import ANALYSIS_SR
from genome.features import HOP
from genome.schema import Section


def segment(features, duration, evidence):
    times = features["times_s"]
    power = features["band_power"]
    width = max(1, round(0.8*ANALYSIS_SR/HOP))
    smooth = uniform_filter1d(power, width, axis=1)
    total = smooth.sum(axis=0)
    descriptor = np.vstack([smooth/(total+1e-12), np.log10(smooth+1e-8)*0.18])
    novelty = np.zeros(len(times))
    if len(times) > 2*width:
        novelty[width:-width] = np.linalg.norm(descriptor[:, 2*width:]-descriptor[:, :-2*width], axis=0)
    novelty = uniform_filter1d(novelty, max(1, width//2))
    threshold = max(0.18, float(np.median(novelty)+2*np.median(np.abs(novelty-np.median(novelty)))))
    points, _ = find_peaks(novelty, height=threshold, prominence=0.12,
                           distance=round(3*ANALYSIS_SR/HOP))
    cuts = [float(times[p]) for p in points if 3 <= times[p] <= duration-3]
    bounds = [0.0, *cuts[:63], duration]
    sections = []
    prototypes = []
    signatures = []
    onset_times = times[features["onset_frames"]]
    for index, (start, end) in enumerate(zip(bounds, bounds[1:])):
        mask = (times >= start)&(times < end)
        bands = power[:, mask].mean(axis=1)
        signature = np.r_[bands/(bands.sum()+1e-12),
                          features["chroma_power"][:, mask].mean(axis=1)/(power[:, mask].sum(axis=0).mean()+1e-12)]
        norm = np.linalg.norm(signature)
        signature /= max(norm, 1e-12)
        signatures.append(signature.copy())
        group = next((i for i, p in enumerate(prototypes) if np.dot(p, signature) > 0.985), len(prototypes))
        if group == len(prototypes):
            prototypes.append(signature)
        ev = evidence("section_summary", start, end, "adjacent_window_feature_novelty",
                      "Candidate section from changes in band balance and energy; functional name unresolved.",
                      {"mean_band_power": bands.tolist(), "onset_count": float(np.sum((onset_times >= start)&(onset_times < end))),
                       "boundary_novelty": float(novelty[np.argmin(np.abs(times-start))])},
                      {"mean_band_power": "window-normalized power, low/mid/high", "onset_count": "events",
                       "boundary_novelty": "descriptor distance, uncalibrated"})
        sections.append(Section(id=f"SEC_{index+1:02}", start_s=start, end_s=end,
                                structure_group=chr(65+group) if group < 26 else f"G{group+1}",
                                evidence_ids=[ev.id], mean_band_power=bands.tolist(),
                                onset_count=int(ev.measurements["onset_count"])))
    features["novelty"] = novelty.astype(np.float32)
    features["section_similarity"] = np.array([[float(np.dot(a, b)) for b in signatures] for a in signatures])
    features["section_midpoints_s"] = np.array([(s.start_s+s.end_s)/2 for s in sections])
    return sections

