# Grounded-answer evaluation

The controlled benchmark is a DSP regression suite. It does not establish that an LLM
using Muvi outperforms raw audio, spectrogram images, or another product.

Run `uv run muvi benchmark --output artifacts/benchmark.json` to regenerate 16 seeded
fixtures. The report includes exact synthesis truth, one-to-one onset metrics,
octave-aware tempo error, section boundary F1 at 0.5/3 seconds, source abstention,
latency percentiles, and sampled process RSS (when psutil is installed). The same
process handles all cases; timings include cache writing and exclude signal synthesis.
They are warm-process machine-specific observations. The scorer penalizes missing,
duplicate, fabricated, and out-of-span responses.

## External-model experiment (not yet run)

Pre-register a model/version, question set, held-out permissioned tracks, token/compute
limits, and a user-important primary metric before collecting results. Keep the same
questions, backbone where possible, and ground truth across these arms:

| Arm | Available inputs |
| --- | --- |
| A | Original audio to an audio-capable model |
| B | Spectrogram image |
| C | Muvi compact digest |
| D | Digest and synchronized tile |
| E | Digest, tile, and on-demand evidence tools |
| F | E plus optional semantic-model hypotheses (not installed) |
| G | F plus optional targeted separation (not installed) |

Capture the model's structured verdict, citations, spans, tokens, wall time and cost.
Two independent listeners should annotate real-track questions and reconcile uncertain
cases. Never force consensus about unidentifiable production sources.

Use `genome.evaluate.score_answers(engine, dataset, answers)` for the machine-checkable
part of grading. For example, one ground-truth item is:

```json
{
  "question_id": "bass-origin-01",
  "track_id": "sha256:<actual-audio-hash>",
  "time_span": {"start_s": 8, "end_s": 12},
  "expected_verdict": "indeterminate",
  "supporting_evidence_ids": ["<actual-record-id>"]
}
```

An answer has `question_id`, `verdict`, `evidence_ids`, and `time_spans` (a list of
`start_s`/`end_s` objects). These example identifiers are placeholders, not evidence.
The function reports citation validity, span support, expected evidence inclusion,
and grounded verdict accuracy. It cannot grade the semantic truth of arbitrary prose;
human review is still required. Unsupported source claims must be counted separately.

Counterfactual conditions should include silence/noise substitution, shifted excerpts,
reordered beats, alternate-bar bass, removed evidence access, and contradictory semantic
hints. No benchmark score, calibrated confidence, or claimed Pareto improvement should
be published without running the corresponding arm.

