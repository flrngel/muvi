"""Deterministic, bounded initial context. JSON remains canonical."""

def track_digest(g, section_offset=0, flow_offset=0):
    from genome.flow import summarize_flow
    flow = summarize_flow(g.sections, g.duration_s, flow_offset)
    flow['parameters_ref'] = g.parameters_sha256
    page = g.sections[section_offset:section_offset+24]
    sections = [s.model_dump() for s in page]
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
             f"objects={','.join(s.sound_object_ids)} evidence={','.join(s.evidence_ids)}" for s in page]
    for row in flow['items']:
        returning = f"; resembles {row['similar_to']['flow_id']} (descriptor hypothesis)" if row['similar_to'] else ''
        text.append(f"FLOW {row['id']} [{row['start_s']:.3f},{row['end_s']:.3f})s {row['description']}{returning}")
    if flow['next_offset'] is not None:
        ending = flow['ending']
        text.append(f"FLOW CONTINUES flow_offset={flow['next_offset']}; ending [{ending['start_s']:.3f},{ending['end_s']:.3f})s {ending['description']}")
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
    tracking = {'available': g.beat_tracking is not None,
                'next_check': 'Use get_beats / muvi beats for paged beat hypotheses and support in an exact window.'}
    if g.beat_tracking:
        bt = g.beat_tracking
        tracking.update(status=bt.status, candidates=[c.model_dump() for c in bt.candidates],
                        beat_count=len(bt.beats), onset_supported_count=sum(b.support == 'onset_supported' for b in bt.beats),
                        evidence_ids=bt.evidence_ids, limitation=bt.limitation)
        text.append(f"BEAT TRACKING {bt.status}; {len(bt.beats)} hypotheses; evidence={','.join(bt.evidence_ids)}; query get_beats")
    return {"title": g.title, "duration_s": g.duration_s, 'flow': flow,
            "texture": next((e.model_dump() for e in g.evidence if e.kind == "spectral_texture"), None),
            "tempo": g.tempo.model_dump(exclude={"beat_times_s"}), "rhythm": rhythm, "beat_tracking": tracking, "sections": sections,
            "section_count": len(g.sections), "sections_truncated": len(g.sections) > 24,
            "section_offset": section_offset,
            "next_section_offset": section_offset+24 if section_offset+24 < len(g.sections) else None,
            "prominent_objects": objects, "patterns": patterns,
            "open_questions": [c.model_dump() for c in g.claims], "digest_text": "\n".join(text),
            "warnings": g.warnings}

