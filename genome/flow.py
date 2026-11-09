"""Bounded acoustic progression derived from stored candidate-section observations."""

import math

from genome.comparison import BANDS, difference, power_change

POWER_TOLERANCE_DB = 3.0
RATE_RELATIVE_TOLERANCE = .25
RATE_ABSOLUTE_TOLERANCE = .5
PAGE_SIZE = 12


def similar(a, b):
    for band in BANDS:
        change = power_change(a['band_mean_power'][band], b['band_mean_power'][band])
        if change['status'] != 'both_zero' and (change['delta_db'] is None or abs(change['delta_db']) > POWER_TOLERANCE_DB):
            return False
    x,y = a['attack_density_per_s'], b['attack_density_per_s']
    return abs(x-y) <= max(RATE_ABSOLUTE_TOLERANCE, RATE_RELATIVE_TOLERANCE*max(x,y))


def measured(sections):
    duration = sum(s.end_s-s.start_s for s in sections)
    powers = {band: sum(s.mean_band_power[i]*(s.end_s-s.start_s) for s in sections)/duration
              for i,band in enumerate(BANDS)}
    total = sum(powers.values())
    dominant = max(powers,key=powers.get) if total > 0 else None
    return {'start_s':sections[0].start_s, 'end_s':sections[-1].end_s,
            'section_ids':[s.id for s in sections], 'evidence_ids':list(dict.fromkeys(e for s in sections for e in s.evidence_ids)),
            'band_mean_power':powers, 'total_mean_power':total,
            'dominant_band':dominant if dominant and powers[dominant]/total >= .6 else 'mixed' if total else None,
            'attack_count':sum(s.onset_count for s in sections),
            'attack_density_per_s':sum(s.onset_count for s in sections)/duration}


def summarize_flow(sections, duration_s, offset=0):
    groups = []
    for section in sections:
        current = measured([section])
        # Compare with the first member as well as the aggregate: no gradual drift collapse.
        if (groups and groups[-1][-1].end_s == section.start_s
                and similar(measured([groups[-1][0]]),current) and similar(measured(groups[-1]),current)):
            groups[-1].append(section)
        else:
            groups.append([section])
    rows = [measured(group) for group in groups]
    peak = max((sum(s.mean_band_power) for s in sections), default=0)
    for i,row in enumerate(rows):
        row['id'] = f'FLOW_{i+1:03}'
        total = row['total_mean_power']
        row['relative_energy_db'] = 10*math.log10(total/peak) if total > 0 and peak > 0 else None
        texture = f"{row['dominant_band']}-dominant" if row['dominant_band'] not in (None,'mixed') else 'mixed-band' if total else 'no measured band energy'
        level = f"{row['relative_energy_db']:.1f} dB vs strongest section" if total else 'zero cached band power'
        row['description'] = f"{texture}; {level}; {row['attack_density_per_s']:.2f} detected attacks/s"
        row['change_from_previous'] = None
        if i:
            previous = rows[i-1]
            changes = {band: power_change(previous['band_mean_power'][band],row['band_mean_power'][band]) for band in BANDS}
            row['change_from_previous'] = {
                'flow_id':previous['id'],
                'band_power':{band:{k:ch[k] for k in ('delta_db','direction','status','within_1_db')} for band,ch in changes.items()},
                'attack_density_per_s':difference(previous['attack_density_per_s'],row['attack_density_per_s'],'detected attacks/s')}
        # Similarity is only a candidate relationship over absolute band power and rate.
        earlier = next((r for r in rows[:max(0,i-1)] if r['total_mean_power'] > 0 and total > 0 and similar(r,row)),None)
        row['similar_to'] = {'flow_id':earlier['id'],'start_s':earlier['start_s'],'end_s':earlier['end_s'],
                              'status':'inferred_descriptor_similarity_not_phrase_identity'} if earlier else None
    return {'method':'section_acoustic_flow_v1', 'method_version':'1',
            'basis':'Duration-weighted stored section mean band powers and detected onset rates; candidate boundaries, not exact source-sample activity.',
            'units':{'band_mean_power':'window-normalized digital power', 'relative_energy_db':'dB relative to strongest stored section',
                     'attack_density_per_s':'detected attacks/s'},
            'thresholds':{'all_bands_within_db':POWER_TOLERANCE_DB, 'attack_rate_absolute_tolerance_per_s':RATE_ABSOLUTE_TOLERANCE,
                          'attack_rate_relative_tolerance':RATE_RELATIVE_TOLERANCE,'calibration':'heuristic_descriptor_tolerances_not_probability'},
            'coverage':{'start_s':0,'end_s':duration_s,'section_count':len(sections)},
            'count':len(rows), 'offset':offset, 'next_offset':offset+PAGE_SIZE if offset+PAGE_SIZE < len(rows) else None,
            'items':rows[offset:offset+PAGE_SIZE], 'ending':rows[-1] if rows else None,
            'limitation':'Acoustic progression only; not source silence, instrument identity, musical form or proof of repeated phrases. Use exact windows for boundary-sensitive questions.'}
