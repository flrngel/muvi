"""Reproducible controlled checks and strict external-answer grounding scoring."""

import json
import tempfile
import threading
import time
from pathlib import Path

import numpy as np

from genome import __version__
from genome.engine import Engine, ANALYSIS_ID
from genome.fixtures import synthesize
from genome.tools import MusicTools


def onset_metrics(expected, observed, tolerance=0.05):
    remaining = set(range(len(observed)))
    errors = []
    for target in expected:
        if not remaining:
            break
        best = min(remaining, key=lambda i: abs(observed[i]-target))
        error = abs(observed[best]-target)
        if error <= tolerance:
            errors.append(error)
            remaining.remove(best)
    precision = len(errors)/len(observed) if len(observed) else float(not len(expected))
    recall = len(errors)/len(expected) if len(expected) else float(not len(observed))
    return {"precision": precision, "recall": recall, "f1": 2*precision*recall/max(precision+recall, 1e-12),
            "median_error_s": float(np.median(errors)) if errors else None, "tolerance_s": tolerance}


def benchmark(output: Path):
    cases = [{"kind": "pulse", "bpm": bpm, "seed": seed, "offset": offset}
             for bpm in [90, 120, 150, 180] for seed, offset in [(7, 0.2), (29, 1.1)]]
    cases += [{"kind": k, "bpm": 150, "seed": 31, "offset": 0.2}
              for k in ["silence", "noise", "tone", "antiphase", "missing", "alternate_bass", "arrangement"]]
    cases += [{"kind": "arrangement", "bpm": 128, "seed": 53, "offset": 0.13}]
    rows, elapsed, peak_rss = [], [], [None]
    stop = threading.Event()
    def sample_memory():
        try:
            import psutil
            process = psutil.Process()
            while not stop.is_set():
                peak_rss[0] = max(peak_rss[0] or 0, process.memory_info().rss)
                stop.wait(0.025)
        except ImportError:
            pass
    sampler = threading.Thread(target=sample_memory, name="muvi-benchmark-memory", daemon=True)
    sampler.start()
    try:
        with tempfile.TemporaryDirectory(prefix="muvi-benchmark-") as temp:
            root = Path(temp)
            engine = Engine(root/"library")
            tools = MusicTools(engine)
            for index, case in enumerate(cases):
                path = root/f"case-{index:02}.wav"
                truth = synthesize(path, duration=16, **case)
                start = time.perf_counter()
                g = engine.analyze(path)
                duration = time.perf_counter()-start
                elapsed.append(duration)
                a = engine.arrays(g.track_id)
                events = a["times_s"][a["onset_frames"]]
                row = {"case_id": f"controlled-{index:02}", "generation": case, "ground_truth": truth,
                       "track_id": g.track_id, "elapsed_s": duration,
                       "source_identity_verdict": tools.verify_hypothesis(g.track_id, "instrument_identity")["verdict"],
                       "candidate_boundaries_s": [s.start_s for s in g.sections[1:]],
                       "tempo_candidates_bpm": g.tempo.candidates_bpm,
                       "digest_characters": len(tools.get_track_digest(g.track_id)["digest_text"])}
                if case["kind"] in ("pulse", "antiphase", "missing"):
                    row["onsets"] = onset_metrics(truth["onsets_s"], events)
                    row["tempo_relative_error"] = min((abs(t-case["bpm"])/case["bpm"] for t in g.tempo.candidates_bpm), default=1)
                if case["kind"] == "arrangement":
                    row["boundary_metrics_0_5s"] = onset_metrics(truth["boundaries_s"], row["candidate_boundaries_s"], 0.5)
                    row["boundary_metrics_3s"] = onset_metrics(truth["boundaries_s"], row["candidate_boundaries_s"], 3)
                if case["kind"] == "silence":
                    row["silence_has_no_events_or_tempo"] = len(events) == 0 and g.tempo.preferred_bpm is None
                rows.append(row)
    finally:
        stop.set()
        sampler.join(timeout=2)
    clean = [r for r in rows if r["generation"]["kind"] == "pulse"]
    gates = {"clean_pulse_f1_at_least_0_90": all(r["onsets"]["f1"] >= 0.9 for r in clean),
             "clean_pulse_median_error_at_most_25ms": all(r["onsets"]["median_error_s"] is not None and r["onsets"]["median_error_s"] <= 0.025 for r in clean),
             "clean_pulse_tempo_error_at_most_3pct": all(r["tempo_relative_error"] <= 0.03 for r in clean),
             "source_identity_abstention": all(r["source_identity_verdict"] == "indeterminate" for r in rows),
             "silence_abstention": next(r["silence_has_no_events_or_tempo"] for r in rows if r["generation"]["kind"] == "silence")}
    result = {"package_version": __version__, "analysis_id": ANALYSIS_ID, "fixture_count": len(rows),
              "scope": "Generated mathematical signals only. Not evidence of general music QA accuracy.",
              "gates": gates, "passed": all(gates.values()),
              "elapsed_p50_s": float(np.median(elapsed)), "elapsed_p95_s": float(np.percentile(elapsed, 95)),
              "sampled_process_peak_rss_bytes": peak_rss[0],
              "external_model_ablations": {arm: "not_run: requires model outputs and permissioned annotated tracks" for arm in "ABCDEFG"},
              "cases": rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result


def score_answers(engine, dataset, answers):
    """Score declared ground truth, ID validity, span support, and abstention. Never grade prose by guessing."""
    cases = {case["question_id"]: case for case in dataset}
    if len(cases) != len(dataset):
        raise ValueError("Duplicate question IDs in ground truth")
    seen, rows = set(), []
    for answer in answers:
        qid = answer["question_id"]
        if qid not in cases or qid in seen:
            raise ValueError("Unknown or duplicate answer question ID")
        seen.add(qid)
        case = cases[qid]
        g = engine.load(case["track_id"])
        evidence = {e.id: e for e in g.evidence}
        ids = answer.get("evidence_ids", [])
        spans = answer.get("time_spans", [])
        ids_valid = bool(ids) and set(ids) <= set(evidence)
        expected_span = case["time_span"]
        span_valid = bool(spans) and all(
            0 <= s["start_s"] < s["end_s"] <= g.duration_s
            and s["start_s"] >= expected_span["start_s"] and s["end_s"] <= expected_span["end_s"]
            and any(evidence[i].start_s <= s["start_s"] and evidence[i].end_s >= s["end_s"] for i in ids if i in evidence)
            for s in spans)
        support = ids_valid and bool(set(ids)&set(case["supporting_evidence_ids"]))
        rows.append({"question_id": qid, "verdict_correct": answer.get("verdict") == case["expected_verdict"],
                     "ids_valid": ids_valid, "timestamp_supported": span_valid, "expected_evidence_cited": support})
    for qid in set(cases)-seen:
        rows.append({"question_id": qid, "verdict_correct": False, "ids_valid": False,
                     "timestamp_supported": False, "expected_evidence_cited": False, "missing_answer": True})
    return {"question_count": len(cases), "rows": rows,
            "grounded_verdict_accuracy": sum(all(r[k] for k in ("verdict_correct", "ids_valid", "timestamp_supported", "expected_evidence_cited")) for r in rows)/max(1, len(cases)),
            "limitation": "Checks declared verdicts and citations, not semantic correctness of free-form prose."}

