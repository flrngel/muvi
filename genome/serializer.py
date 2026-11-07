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
    return {"title": g.title, "duration_s": g.duration_s,
            "tempo": g.tempo.model_dump(exclude={"beat_times_s"}), "sections": sections,
            "section_count": len(g.sections), "sections_truncated": len(g.sections) > 24,
            "prominent_objects": objects, "patterns": patterns,
            "open_questions": [c.model_dump() for c in g.claims], "digest_text": "\n".join(text),
            "warnings": g.warnings}

