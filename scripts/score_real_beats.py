"""Score exported genomes against a local, provenance-preserving RWC manifest.

Usage: python scripts/score_real_beats.py MANIFEST BASELINE_EXPORT_DIR TUNED_EXPORT_DIR OUTPUT
No downloads or phase/metrical corrections. Both directories contain CASE-export.json.
"""

import csv
import json
import statistics
import sys
from pathlib import Path


def match_beats(reference, prediction, tolerance=.07):
    """Ordered one-to-one maximum-cardinality matches within the fixed tolerance."""
    i, j, errors = 0, 0, []
    while i < len(reference) and j < len(prediction):
        delta = prediction[j]-reference[i]
        if abs(delta) <= tolerance:
            errors.append(abs(delta))
            i, j = i+1, j+1
        elif delta < 0:
            j += 1
        else:
            i += 1
    p = len(errors)/len(prediction) if prediction else 0
    r = len(errors)/len(reference) if reference else 0
    return dict(precision=p, recall=r, f1=2*p*r/(p+r) if p+r else 0,
                reference_count=len(reference), predicted_count=len(prediction), matches=len(errors),
                median_error_s=statistics.median(errors) if errors else None)


def tempo(times):
    return 60/statistics.median([b-a for a, b in zip(times, times[1:])]) if len(times) >= 2 else None


def score(manifest, baseline, tuned):
    rows = []
    for case in manifest['tracks']:
        annotations = []
        with Path(case['annotation_path']).open(encoding='utf-8-sig', newline='') as handle:
            for row in csv.reader(handle, delimiter=';'):
                try:
                    annotations.append(float(row[0])-case['source_start_s'])
                except (ValueError, IndexError):
                    continue
        reference = sorted(t for t in annotations if 5 <= t < 45)
        assert reference, f"No references: {case['case_id']}"
        item = dict(case_id=case['case_id'], rwc_id=case['rwc_id'], reference_tempo_bpm=tempo(reference))
        for label, folder in [('baseline', baseline), ('tuned', tuned)]:
            g = json.loads((folder/f"{case['case_id']}-export.json").read_text(encoding='utf-8'))
            tracking = g.get('beat_tracking')
            times = [b['time_s'] for b in tracking['beats']] if tracking else g['tempo']['beat_times_s']
            times = [t for t in times if 5 <= t < 45]
            result = match_beats(reference, times)
            rate = tempo(times)
            result['predicted_tempo_bpm'] = rate
            result['preferred_global_bpm'] = g['tempo']['preferred_bpm']
            ratio = rate/item['reference_tempo_bpm'] if rate else None
            result['strict_tempo_relative_error'] = abs(ratio-1) if ratio else None
            result['octave_tempo_relative_error'] = min(abs(ratio*2**n-1) for n in (-1,0,1)) if ratio else None
            result['analysis_id'] = g['analysis_id']
            if tracking:
                supported = [b['time_s'] for b in tracking['beats'] if b['support'] == 'onset_supported' and 5 <= b['time_s'] < 45]
                result['supported_only'] = match_beats(reference, supported)
                result['onset_supported_fraction'] = len(supported)/len(times) if times else 0
                result['window_availability'] = []
                for start in (5,15,25,35):
                    window = [t for t in times if start <= t < start+10]
                    support = [t for t in supported if start <= t < start+10]
                    available = len(window) >= 4 and len(support)/len(window) >= .5
                    result['window_availability'].append(dict(start_s=start,end_s=start+10,inferred=available))
            item[label] = result
        rows.append(item)
    means = {label: statistics.mean(r[label]['f1'] for r in rows) for label in ('baseline','tuned')}
    return dict(protocol='Fixed six RWC 2.0 excerpts; original [30,75); evaluate excerpt [5,45); strict metrical level, one-to-one 70ms; no post-hoc offset or tempo rescaling',
                macro_f1=means, cases=rows)


if __name__ == '__main__':
    manifest_path, baseline, tuned, output = map(Path, sys.argv[1:])
    result = score(json.loads(manifest_path.read_text()), baseline, tuned)
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'macro_f1':result['macro_f1'], 'cases':[
        {'id':r['rwc_id'],'baseline_f1':r['baseline']['f1'],'tuned_f1':r['tuned']['f1'],
         'reference_bpm':r['reference_tempo_bpm'],'predicted_bpm':r['tuned']['predicted_tempo_bpm']} for r in result['cases']]},indent=2))
