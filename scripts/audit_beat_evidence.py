"""Check that cited measurements were actually returned in recorded tool calls."""

import argparse
import json
from pathlib import Path


def packets(log):
    text = log.read_text(encoding='utf-8')
    rows = json.loads(text) if log.suffix == '.json' else [json.loads(line) for line in text.splitlines() if line]
    for row in rows:
        if 'stdout' in row:
            if row.get('exit_code', 0) != 0:
                continue
            try:
                yield json.loads(row['stdout'])
            except json.JSONDecodeError:
                continue
        elif 'response' in row:
            response = row['response']
            if response.get('isError'):
                continue
            structured = response.get('structuredContent')
            if structured:
                yield structured.get('result', structured)
            else:
                for block in response.get('content', []):
                    if block.get('type') == 'text':
                        try:
                            yield json.loads(block['text'])
                        except json.JSONDecodeError:
                            continue


def audit(answers, logs):
    retrieved = set()
    for log in logs:
        for packet in packets(Path(log)):
            if isinstance(packet, dict) and packet.get('track_id') and packet.get('analysis_id'):
                for item in packet.get('evidence', []):
                    retrieved.add((packet['track_id'], packet['analysis_id'], item['id']))
    rows = []
    for answer in answers['answers']:
        missing = [ref for ref in answer['evidence_ids'] if
                   (answer['track_id'], answer['analysis_id'], ref) not in retrieved]
        rows.append({'case_id':answer['case_id'], 'all_citations_retrieved':not missing, 'missing':missing})
    return {'model': answers['model'], 'condition':answers['condition'],
            'all_citations_retrieved':all(r['all_citations_retrieved'] for r in rows), 'rows':rows}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('answers', type=Path)
    parser.add_argument('logs', type=Path, nargs='+')
    args=parser.parse_args()
    print(json.dumps(audit(json.loads(args.answers.read_text(encoding='utf-8')),args.logs),indent=2))
