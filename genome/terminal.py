"""Dependency-free terminal presentation. JSON output never passes through here."""

import json
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


def table(headers, rows):
    rows = [[clean(value) for value in row] for row in rows]
    if not rows:
        return "  No matches."
    widths = [max(len(h), *(len(row[i]) for row in rows)) for i, h in enumerate(headers)]
    return "\n".join("  " + "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
                     for row in [headers, *rows])


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
