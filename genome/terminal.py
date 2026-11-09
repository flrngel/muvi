"""Dependency-free terminal presentation. JSON output never passes through here."""

import json
import shutil
import unicodedata


def clean(value):
    # Filenames and imported titles are untrusted terminal text, not ANSI instructions.
    return "".join(c if not unicodedata.category(c).startswith("C") else " " for c in str(value))


def clock(seconds):
    minutes, seconds = divmod(float(seconds), 60)
    return f"{int(minutes):02}:{seconds:06.3f}"


def span(item):
    return f"{clock(item['start_s'])} - {clock(item['end_s'])}"


def short(track):
    return track.removeprefix("sha256:")[:12]


def cell_width(value):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in value)


def columns():
    return max(20, shutil.get_terminal_size(fallback=(100, 24)).columns)


def fold(value, width):
    """Wrap by terminal cells, retaining long identifiers and combining marks."""
    lines = []
    while cell_width(value) > width:
        used = 0
        cut = 0
        for char in value:
            used += cell_width(char)
            if used > width:
                break
            cut += 1
        space = value.rfind(' ', 0, cut+1)
        if space > 0:
            cut = space
        cut = max(1, cut)
        lines.append(value[:cut].rstrip())
        value = value[cut:].lstrip()
    return [*lines, value]


def table(headers, rows):
    rows = [[clean(value) for value in row] for row in rows]
    if not rows:
        return "  No matches."
    widths = [max(cell_width(h), *(cell_width(row[i]) for row in rows)) for i, h in enumerate(headers)]
    available = columns()-2-2*(len(headers)-1)
    minimum = [min(w, max(cell_width(h), 23 if h in ('TIME', 'ORIGINAL TIME') and w > 20 else 12))
               for h, w in zip(headers, widths)]
    if sum(minimum) > available:
        return '\n\n'.join('\n'.join(f'  {h}: {v}' for h, v in zip(headers, row)) for row in rows)
    while sum(widths) > available:
        i = max((i for i in range(len(widths)) if widths[i] > minimum[i]), key=lambda i: widths[i])
        widths[i] -= 1
    lines = []
    for row in [headers, *rows]:
        cells = [fold(value, width) for value, width in zip(row, widths)]
        for line in range(max(map(len, cells))):
            parts = [cell[line] if line < len(cell) else '' for cell in cells]
            lines.append('  '+'  '.join(value+' '*(width-cell_width(value)) for value, width in zip(parts, widths)).rstrip())
    return '\n'.join(lines)


def sections(items):
    return table(["SECTION", "ORIGINAL TIME", "GROUP", "SOUNDS", "EVIDENCE"],
                 [[s['id'], span(s), s['structure_group'], ", ".join(s['sound_object_ids']) or "-",
                   ", ".join(s['evidence_ids'])] for s in items])


def pretty(value, indent=0):
    """Readable fallback for detailed typed tool payloads; no data is silently discarded."""
    pad = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            label = clean(key).replace("_", " ")
            if isinstance(item, (dict, list)) and item:
                lines.extend([f"{pad}{label}:", pretty(item, indent + 2)])
            else:
                lines.append(f"{pad}{label}: {scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        if all(not isinstance(x, (dict, list)) for x in value):
            return pad + ", ".join(scalar(x) for x in value)
        return "\n".join(pad + "- " + pretty(x, indent + 2).lstrip() for x in value)
    return pad + scalar(value)


def scalar(value):
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (list, dict, bool)):
        return clean(json.dumps(value, ensure_ascii=False))
    return clean(value)


def format_result(command, result):
    lines = []
    for line in _format_result(command, result).split('\n'):
        line = clean(line)
        indent = min(len(line)-len(line.lstrip()), columns()//2)
        lines.extend(' '*indent + part for part in fold(line[indent:], columns()-indent))
    return '\n'.join(lines)


def _format_result(command, result):
    if command in ("analyze", "inspect", "overview", "demo"):
        tempo = result['tempo']
        bpm = tempo['preferred_bpm']
        lines = [f"{clean(result['title'])}  |  {clock(result['duration_s'])}",
                 f"Track     {short(result['track_id'])}",
                 f"Analysis  {result['analysis_id']}",
                 f"Tempo     {f'{bpm:g} BPM (provisional)' if bpm else 'unresolved'}",
                 f"Candidates  {', '.join(f'{x:g}' for x in tempo['candidates_bpm']) or 'none'} BPM; uncalibrated ranking",
                 "", "Candidate sections", sections(result['sections']), "", "Acoustic sounds",
                 table(["ID", "DESCRIPTION", "EVENTS", "EVIDENCE"],
                       [[s['id'], s['name'], s['occurrence_count'], ", ".join(s['evidence_ids'])]
                        for s in result['prominent_objects']])]
        if result['sections_truncated']:
            lines.append(f"  Showing 24 of {result['section_count']}; use muvi sections for all sections.")
        flow = result['flow']
        progression = ['', 'Acoustic progression', table(['FLOW','TIME','OBSERVATIONS','RESEMBLES'],
                       [[row['id'],span(row),row['description'],row['similar_to']['flow_id'] if row['similar_to'] else '']
                        for row in flow['items']])]
        if flow['next_offset'] is not None:
            progression.extend([f"Continue: muvi inspect {short(result['track_id'])} --flow-offset {flow['next_offset']}",
                                f"Ending {flow['ending']['id']} {span(flow['ending'])}: {flow['ending']['description']}"])
        progression.append('Candidate boundaries and descriptor similarity; use exact windows for source silence.')
        lines[6:6] = progression
        if result['patterns']:
            lines.extend(["", "Repetition", table(["ID", "SOUND", "INTERVAL", "REPEATS", "EXCEPTIONS"],
                         [[p['id'], p['sound_object_id'], f"{p['interval_s']:.3f}s", p['repeat_count'],
                           p['exception_count']] for p in result['patterns']])])
        lines.extend(["", "Limits: source identity, meter/downbeat and independent bass remain unresolved."])
        lines.extend(f"  {clean(w)}" for w in result['warnings'])
        lines.extend(["", f"Next: muvi sounds {short(result['track_id'])} --query bass",
                      f"      muvi inspect {short(result['track_id'])} --json"])
        return "\n".join(lines)
    if command == "list":
        if not result['tracks']:
            return "Your library is empty. Run muvi analyze <audio> or muvi demo."
        return table(["TRACK", "TITLE", "DURATION", "BPM", "PIPELINE"],
                     [[short(t['track_id']), t['title'], clock(t['duration_s']),
                       f"{t['tempo_bpm']:g}" if t['tempo_bpm'] else "?", t['analysis_id']]
                      for t in result['tracks']])
    if command == 'compare' and result.get('comparison_basis') == 'exact_requested_windows':
        changes = result['changes']
        rows = [[band,scalar(c['delta_db']),c['direction'],c['status'],
                 scalar(changes['band_attack_density_per_s'][band]['delta'])]
                for band,c in changes['band_power'].items()]
        return '\n'.join([f"COMPARE A {span(result['window_a']['time_span'])} -> B {span(result['window_b']['time_span'])}",
                          'Changes are B minus A; attack rates normalize unequal durations.',
                          table(['BAND','POWER dB','DIRECTION','BASIS','ATTACKS/s CHANGE'],rows),
                          f"Source RMS change: {scalar(changes['source_rms_dbfs']['delta'])} dB",
                          f"Activity: {result['window_a']['source_activity']} -> {result['window_b']['source_activity']}",
                          'Evidence: '+', '.join(result['evidence_ids']),result['limitation']])
    if command == "window":
        bands = result['bands']
        return '\n'.join([f"WINDOW  |  {span(result['time_span'])}",
                          f"Activity  {result['source_activity']}  |  RMS {scalar(result['source_rms_dbfs'])} dBFS",
                          table(['BAND', 'POWER', 'FRACTION'], [[name, scalar(v['mean_power']), scalar(v['fraction'])] for name,v in bands.items()]),
                          f"Attacks  {result['attack_count']}  |  {result['attack_density_per_s']:.3f}/s (not beats)",
                          f"Beat tempo  {scalar(result['beats'].get('local_tempo_bpm'))} BPM (inferred)",
                          'Evidence  '+', '.join(result['evidence_ids']),
                          'Band fractions describe balance; source identity and meter remain unresolved.'])
    if command == "sections" and "sections" in result:
        return sections(result['sections'])
    if command == "sounds":
        return table(["SOUND", "DESCRIPTION", "EVENTS", "EVIDENCE"],
                     [[s['sound_object_id'], s['name'], s['occurrences_in_span'], ", ".join(s['evidence_ids'])]
                      for s in result['matches']]) + "\n\n" + result['limitation']
    if command == "verify":
        return "\n".join([f"{result['verdict'].upper()}: {result['conclusion']}",
                          f"Evidence: {', '.join(result['evidence_ids']) or 'none'}",
                          f"Next: {result['next_check']}"])
    if command == "beats":
        if not result['available']:
            return result['reason'] + "\n" + result['next_check']
        rate = result['local_tempo_bpm']
        return "\n".join([f"TRACKED BEAT HYPOTHESES  |  {span(result['time_span'])}",
                          f"Local tempo  {f'{rate:g} BPM (inferred)' if rate else 'unresolved'}",
                          f"Onset support  {result['onset_supported_count']}/{result['beat_count']}",
                          table(['TIME', 'SUPPORT'], [[f"{b['time_s']:.3f}s", b['support']] for b in result['beats'][:16]]),
                          'Use --json and --offset/--limit for the complete sequence.',
                          result['limitation']])
    if command == "rhythm":
        if not result['available']:
            return result['reason'] + "\n" + result['next_check']
        bpm = result['pulse']['pulse_rate_bpm']
        events = result['onset_times_s']
        lines = [f"{result['band'].upper()} band  |  {span(result['time_span'])}",
                 f"Acoustic pulse  {f'{bpm:g} pulses/min (inferred)' if bpm else 'unresolved'}",
                 f"Track timing    {result['track_timing_status']}",
                 f"Detected attacks in interval: {result['event_count']}",
                 "First returned attacks: " + (", ".join(f"{t:.3f}s" for t in events[:12]) or "none")]
        if len(events) > 12 or result['next_offset'] is not None:
            lines.append("Use --json and --offset/--limit to retrieve all detected attacks.")
        lines.extend(["", "Long gaps between detected attacks", table(["ORIGINAL TIME", "DURATION"],
                      [[span(g), f"{g['duration_s']:.3f}s"] for g in result['long_gaps']]),
                      "", result['limitation'], result['grid_warning']])
        return "\n".join(lines)
    if command in ("crop", "render"):
        lines = [f"Original time  {span(result['time_span'])}", f"Analysis       {result['analysis_id']}"]
        lines.extend(f"{key.capitalize():14} {clean(result[key]['path'])}"
                     for key in ("audio", "image", "legend") if key in result)
        if command == "crop":
            lines.append("Original mixture; source samples retained without gain normalization.")
        return "\n".join(lines)
    if command == "export":
        return f"Saved canonical genome: {clean(result['path'])}\nAnalysis: {result['analysis_id']}"
    if command == "tools" and "tools" in result:
        return table(["TOOL", "PURPOSE"], [[t['name'], t['description']] for t in result['tools']])
    if command == "benchmark":
        return f"Benchmark: {'PASS' if result['passed'] else 'FAIL'}\n" + pretty(result)
    return pretty(result)
