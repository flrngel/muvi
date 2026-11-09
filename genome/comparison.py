"""Arithmetic on existing observations, with explicit zero and missing semantics."""

import math

BANDS = ('low', 'mid', 'high')


def difference(a, b, unit):
    delta = b-a if a is not None and b is not None else None
    return {'a': a, 'b': b, 'delta': delta, 'unit': unit,
            'direction': 'unavailable' if delta is None else
                         'increased' if delta > 0 else 'decreased' if delta < 0 else 'unchanged'}


def power_change(a, b):
    result = difference(a, b, 'window-normalized digital power')
    if a is None or b is None:
        status, db = 'unavailable', None
    elif a == 0 or b == 0:
        status = 'both_zero' if a == b else 'from_zero' if a == 0 else 'to_zero'
        db = None
    else:
        status, db = 'finite', 10*(math.log10(b)-math.log10(a))
    return {**result, 'status': status, 'delta_db': db,
            'within_1_db': abs(db) <= 1 if db is not None else None}


def band_rates(window):
    duration = window['time_span']['end_s']-window['time_span']['start_s']
    return {band: window['band_attacks'][band]['event_count']/duration
            if band in window['band_attacks'] else None for band in BANDS}


def compare_windows(a, b):
    rates_a, rates_b = band_rates(a), band_rates(b)
    changes = {'band_power': {band: power_change(a['bands'][band]['mean_power'], b['bands'][band]['mean_power'])
                              for band in BANDS},
               'band_attack_density_per_s': {band: difference(rates_a[band], rates_b[band], 'detected attacks/s')
                                             for band in BANDS}}
    for key, unit in [('source_rms_dbfs','dBFS; delta in dB'), ('attack_density_per_s','detected attacks/s'),
                      ('energy_weighted_centroid_hz','Hz'), ('harmonic_like_ratio','texture ratio')]:
        changes[key] = difference(a[key], b[key], unit)
    return changes


def snapshot(window):
    keys = ('time_span', 'source_activity', 'source_rms_dbfs', 'bands', 'attack_count',
            'attack_density_per_s', 'energy_weighted_centroid_hz', 'harmonic_like_ratio', 'measurement_basis')
    return {**{key: window[key] for key in keys}, 'band_attack_density_per_s': band_rates(window),
            'evidence_ids': [i for i in window['evidence_ids'] if i.startswith('W')]}


def synopsis(a, b, changes):
    def span(w):
        return f"[{w['time_span']['start_s']:g},{w['time_span']['end_s']:g})s"
    def number(value):
        return f'{value:.4g}' if value is not None else 'unavailable'
    power = []
    rates = []
    for band in BANDS:
        p = changes['band_power'][band]
        power.append(f"{band} {number(p['delta_db'])} dB ({p['status']})")
        r = changes['band_attack_density_per_s'][band]
        rates.append(f"{band} {number(r['a'])}->{number(r['b'])}/s ({r['direction']})")
    return (f"A {span(a)}; B {span(b)}. Band-power changes B minus A: {'; '.join(power)}. "
            f"Detected band-attack rates A->B: {'; '.join(rates)}. "
            f"Overall detected attack rate {number(a['attack_density_per_s'])}->{number(b['attack_density_per_s'])}/s. "
            f"Source activity {a['source_activity']}->{b['source_activity']}. "
            "Zero band power is 0; its dB level is null. Similar energy does not establish similar rates in every band.")
