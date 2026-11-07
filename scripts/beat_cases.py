"""Deterministic blind rhythm corpus. Evaluators must not read this file or truth.json."""

import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt


def make_case(path, kind, bpm, offset, seed, duration=20):
    sr = 22050
    rng = np.random.default_rng(seed)
    audio = np.zeros((round(duration*sr), 2))
    low = []
    t = offset
    index = 0
    while t < duration - 0.25:
        rate = bpm
        if kind == 'change' and t >= duration/2:
            rate = bpm*1.5
        if kind == 'drift':
            rate = bpm*(1 + 0.5*t/duration)
        if kind != 'noise' and not (kind == 'missing' and index % 11 in (5, 6)) and not (
                kind == 'break' and duration*0.35 <= t < duration*0.6):
            low.append(round(t*sr)/sr)
        t += 60/rate
        index += 1

    def add(start, samples, gain=1, pan=0):
        i = round(start*sr)
        samples = samples[:len(audio)-i]*gain
        audio[i:i+len(samples), 0] += samples*(1-pan*0.3)
        audio[i:i+len(samples), 1] += samples*(1+pan*0.3)

    x = np.arange(round(.19*sr))/sr
    for i, t in enumerate(low):
        pulse = np.sin(2*np.pi*(51*x+2.7*(1-np.exp(-35*x))))*np.exp(-x*26)
        pulse += rng.normal(0, .07, len(x))*np.exp(-x*180)
        add(t, pulse, .55 if kind != 'subdivisions' else .3)
    if kind in ('swing', 'subdivisions'):
        for t in np.arange(offset, duration-.1, 60/bpm):
            for fraction in ([0, 2/3] if kind == 'swing' else [0, .25, .5, .75]):
                start = t + fraction*60/bpm
                if start >= duration-.1:
                    continue
                x = np.arange(round(.045*sr))/sr
                noise = sosfilt(butter(3, 5000, 'highpass', fs=sr, output='sos'), rng.normal(size=len(x)))
                add(start, noise*np.exp(-x*90), .13 if kind == 'swing' else .4, .5)
    if kind == 'noise':
        audio = rng.normal(0, .025, audio.shape)
    sf.write(path, audio, sr, subtype='PCM_24')
    probes = [{'start_s': 1.5, 'end_s': 6.5}, {'start_s': duration-6.5, 'end_s': duration-1.5}]
    rates = []
    for probe in probes:
        events = np.array([t for t in low if probe['start_s'] <= t < probe['end_s']])
        # Missing pulses are whole-cycle omissions; physical base pulse rate is the
        # shortest established interval in the window, not the inverse average gap.
        intervals = np.diff(events)
        value = None if not len(intervals) else 60/float(np.median(intervals[intervals < np.median(intervals)*1.4]))
        rates.append({**probe, 'bpm': value})
    return {'kind': kind, 'nominal_bpm': bpm, 'seed': seed, 'duration_s': duration,
            'pulse_present': bool(low), 'pulse_times_s': low, 'first_pulse_times_s': low[:5],
            'local_rates': rates, 'long_gaps': [{'start_s': a, 'end_s': b} for a, b in zip(low, low[1:]) if b-a > 2],
            'meter_verdict': 'indeterminate', 'independent_bass_verdict': 'indeterminate'}


def generate(root):
    root = Path(root)
    kinds = ['steady', 'missing', 'change', 'break', 'noise', 'swing', 'drift', 'subdivisions']
    questions = {
        'pulse_present': 'Is a recurring low-frequency transient pulse established? Return true/false/null.',
        'local_rates': 'For each supplied window estimate the base low-transient acoustic pulse rate in BPM. This is not a claim of unique musical tempo. Use null if unavailable.',
        'first_pulse_times_s': 'Return the first five observed low-pulse attacks, not extrapolated beat-grid positions. Return [] if none established.',
        'long_gaps': 'Return intervals between consecutive low-pulse attacks exceeding 2 seconds, measured from the last attack to the next attack. Exclude leading/trailing margins.',
        'meter_verdict': 'Can the evidence establish musical meter and downbeat? supported or indeterminate.',
        'independent_bass_verdict': 'Can it prove a separate bass instrument/source? supported or indeterminate.',
        'citations': 'Include retrieved evidence_ids, track_id, analysis_id and time_spans covering your claims.',
    }
    for split, ids, rates, seed in [
        ('development', ['r17', 'r42', 'r08', 'r63', 'r25', 'r91', 'r36', 'r54'],
         [120, 137, 96, 128, 115, 112, 90, 150], 401),
        ('heldout', ['r73', 'r14', 'r68', 'r39', 'r02', 'r85', 'r47', 'r96'],
         [103, 157, 110, 143, 123, 126, 106, 134], 819),
    ]:
        folder = root/split
        folder.mkdir(parents=True, exist_ok=True)
        public, truth = [], []
        for i, (case_id, kind, bpm) in enumerate(zip(ids, kinds, rates)):
            audio = folder/f'{case_id}.wav'
            data = make_case(audio, kind, bpm, .37 if split == 'development' else .613, seed+i,
                             20 if split == 'development' else 22)
            public.append({'case_id': case_id, 'audio_path': str(audio.resolve()), 'duration_s': data['duration_s'],
                           'probes': [{k:v for k,v in p.items() if k != 'bpm'} for p in data['local_rates']]})
            truth.append({'case_id': case_id, **data})
        (folder/'public.json').write_text(json.dumps({'questions': questions, 'cases': public}, indent=2), encoding='utf-8')
        (folder/'truth.json').write_text(json.dumps(truth, indent=2), encoding='utf-8')


if __name__ == '__main__':
    generate(Path('artifacts/beat-eval/corpus'))
