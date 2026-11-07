"""Deterministic, bounded initial context. JSON remains canonical."""

def track_digest(g):
    sections = [s.model_dump() for s in g.sections[:24]]
    objects = [{"id": s.id, "name": s.name, "form": s.form,
                "function_candidates": s.function_candidates, "source_status": s.source_status,
                "occurrence_count": s.occurrence_count, "evidence_ids": s.evidence_ids}
               for s in g.sound_objects]
    patterns = [p.model_dump() for p in g.patterns[:8]]
    for p in patterns:
        p["exception_count"] = len(p["exceptions_s"])
        p["exceptions_s"] = p["exceptions_s"][:16]
    text = [f"TRACK {g.track_id} | {g.title} | {g.duration_s:.3f}s | analysis={g.analysis_id}",
            f"TEMPO candidates={g.tempo.candidates_bpm} BPM; preferred={g.tempo.preferred_bpm}; "
            "uncalibrated ranking; meter/downbeat unknown"]
    text += [f"SECTION {s.id} group={s.structure_group} [{s.start_s:.3f},{s.end_s:.3f})s "
             f"objects={','.join(s.sound_object_ids)} evidence={','.join(s.evidence_ids)}" for s in g.sections[:24]]
    text += [f"SOUND {s.id} {s.name}; roles={','.join(s.function_candidates)}; source=UNRESOLVED; "
             f"events={s.occurrence_count}; evidence={','.join(s.evidence_ids)}" for s in g.sound_objects]
    text += [f"PATTERN {p.id} {p.sound_object_id} every ~{p.interval_s:.3f}s x{p.repeat_count}; "
             f"exceptions={len(p.exceptions_s)}; evidence={','.join(p.evidence_ids)}" for p in g.patterns[:8]]
    text += ["UNKNOWN independent bass vs pulse tail: indeterminate. Objects may represent mixtures.",
             "NEXT query get_section/get_sound/get_evidence; audition original crops before source claims."]
    rhythm = {"available": g.rhythm is not None, "streams": [],
              "next_check": "Use get_rhythm with a band and exact interval for pulse rates, attack times and gaps. Global BPM is not a local rate or proven meter."}
    if g.rhythm:
        for stream in g.rhythm.streams:
            rates = [w.pulse.pulse_rate_bpm for w in stream.local_windows if w.pulse.pulse_rate_bpm is not None]
            rhythm['streams'].append({'band': stream.band, 'timing_status': stream.timing_status,
                                      'detected_attack_count': len(stream.onset_times_s),
                                      'pulse_rate_bpm': stream.pulse.pulse_rate_bpm,
                                      'local_rate_range_bpm': [min(rates), max(rates)] if rates else [],
                                      'evidence_ids': stream.evidence_ids})
            text.append(f"RHYTHM {stream.band}: {stream.timing_status}; acoustic pulse={stream.pulse.pulse_rate_bpm}; "
                        f"events={len(stream.onset_times_s)}; evidence={','.join(stream.evidence_ids)}")
    return {"title": g.title, "duration_s": g.duration_s,
            "texture": next((e.model_dump() for e in g.evidence if e.kind == "spectral_texture"), None),
            "tempo": g.tempo.model_dump(exclude={"beat_times_s"}), "rhythm": rhythm, "sections": sections,
            "section_count": len(g.sections), "sections_truncated": len(g.sections) > 24,
            "prominent_objects": objects, "patterns": patterns,
            "open_questions": [c.model_dump() for c in g.claims], "digest_text": "\n".join(text),
            "warnings": g.warnings}

