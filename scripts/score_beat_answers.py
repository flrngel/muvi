"""Score blind agent answers against fixed generated-event truth; no prose grading."""

import argparse
import json
import math
from pathlib import Path

from genome.engine import Engine
from genome.evaluate import onset_metrics


def score(truth, response, library):
    answers = {a['case_id']: a for a in response['answers']}
    if len(answers) != len(response['answers']):
        raise ValueError('Duplicate case IDs in answers')
    known = {t['case_id'] for t in truth}
    if set(answers) - known:
        raise ValueError('Unknown case IDs in answers')
    engine = Engine(library)
    rows = []
    for expected in truth:
        answer = answers.get(expected['case_id'], {})
        rates = answer.get('local_rates', [])
        rate_scores = []
        for probe in expected['local_rates']:
            matches = [p for p in rates if abs(p['start_s']-probe['start_s']) < .001 and abs(p['end_s']-probe['end_s']) < .001]
            value = matches[0].get('bpm') if len(matches) == 1 else None
            valid = len(matches) == 1 and ((value is None and probe['bpm'] is None) or
                    (isinstance(value, (float, int)) and probe['bpm'] is not None and math.isfinite(value)
                     and abs(value-probe['bpm'])/probe['bpm'] <= .05))
            rate_scores.append(bool(valid))
        gaps = answer.get('long_gaps', [])
        wanted_gaps = expected['long_gaps']
        gap_score = len(gaps) == len(wanted_gaps) and all(
            abs(a['start_s']-b['start_s']) <= .12 and abs(a['end_s']-b['end_s']) <= .12
            for a, b in zip(sorted(gaps, key=lambda x:x['start_s']), wanted_gaps))
        first = answer.get('first_pulse_times_s', [])
        timing = onset_metrics(expected['first_pulse_times_s'], first)
        citations_valid = False
        try:
            g = engine.load(answer.get('track_id', ''), answer.get('analysis_id'))
            refs = answer.get('evidence_ids', [])
            spans = answer.get('time_spans', [])
            lookup = {e.id:e for e in g.evidence}
            citations_valid = bool(refs and spans) and set(refs) <= set(lookup) and all(
                0 <= p['start_s'] < p['end_s'] <= g.duration_s and any(
                    lookup[e].start_s <= p['start_s'] and lookup[e].end_s >= p['end_s'] for e in refs)
                for p in spans)
        except (KeyError, ValueError):
            pass
        rows.append({'case_id': expected['case_id'], 'kind': expected['kind'],
                     'pulse_presence': answer.get('pulse_present') is expected['pulse_present'],
                     'local_rates': rate_scores, 'first_attack_times': 'first_pulse_times_s' in answer and timing['f1'] >= .9,
                     'first_attack_f1': timing['f1'], 'long_gaps': 'long_gaps' in answer and gap_score,
                     'meter_abstention': answer.get('meter_verdict') == 'indeterminate',
                     'source_abstention': answer.get('independent_bass_verdict') == 'indeterminate',
                     'citation_validity': citations_valid})
    summary = {key:{'correct':sum(r[key] for r in rows), 'total':len(rows)} for key in
               ['pulse_presence', 'first_attack_times', 'long_gaps', 'meter_abstention', 'source_abstention', 'citation_validity']}
    summary['local_rates'] = {'correct':sum(sum(r['local_rates']) for r in rows),
                              'total':sum(len(r['local_rates']) for r in rows)}
    return {'model':response['model'],'transport':response['transport'],'condition':response['condition'],
            'summary':summary, 'rows':rows,
            'limitations':['Small deterministic synthetic corpus, not real-music beat understanding.',
                          'Citation validity checks IDs and spans; actual retrieval must also be audited against logs.',
                          'Model and transport are confounded; agents can learn between conditions.']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('truth', type=Path)
    parser.add_argument('answers', type=Path)
    parser.add_argument('library', type=Path)
    parser.add_argument('output', type=Path)
    args=parser.parse_args()
    report=score(json.loads(args.truth.read_text()),json.loads(args.answers.read_text(encoding='utf-8')),args.library)
    args.output.parent.mkdir(exist_ok=True, parents=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report['summary'],indent=2))
