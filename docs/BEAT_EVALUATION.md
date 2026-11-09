# Independent Terra / Luna rhythm evaluation

2026-11-06. The user requested two independent agents to test actual LLM consumption
through MCP or a skill, then tune demonstrated weaknesses. Terra (`gpt-6.1-terra`)
used real MCP stdio; Luna (`gpt-6-luna`) used the CLI and, for the tuned condition,
the [Muvi skill](../skills/muvi/SKILL.md). Both started without parent history.

## What was tested

The [protocol](BEAT_EVAL_PLAN.md) and scoring rules preceded answer collection.
Eight development and eight held-out recordings were synthesized with exact attack
times: steady pulse, missing attacks, abrupt tempo change, a break, stationary noise,
swing subdivisions, gradual tempo drift and dominant bright subdivisions. Held-out
cases changed rates, seeds, offsets and duration; they share the generator families.

Agents received anonymous paths and questions, not the generator, truth, production
code or each other's answers. They could calculate intervals from retrieved events.
Each evaluated held-out cases with frozen 0.4.0 first, then frozen 0.5.0. Root did not
give truth feedback and verified that production/skill hashes remained unchanged.

These are **acoustic pulse and evidence-use tests on generated signals**, not a claim
about human-perceived beats in arbitrary mastered music. No direct-audio LLM arm was
run. Procedural blinding was instructed and followed in recorded work, not enforced
by separate operating-system permissions. Each model/condition has one trajectory;
order, case reuse, model and transport are confounds. Do not interpret this as a
model leaderboard or a statistically established general improvement.

## Held-out results

Rates use the preregistered 5% tolerance without half/double credit; the question asks
for the base low-transient acoustic pulse rate, not unique musical tempo. First attacks
use one-to-one 50 ms matching. Gaps use 120 ms endpoint tolerance.

| Component | Terra MCP, before → after | Luna CLI/skill, before → after |
| --- | --- | --- |
| Local pulse-rate answers | **14/16 → 16/16** | **14/16 → 16/16** |
| First five low-attack times | **7/8 → 8/8** | 8/8 → 8/8 |
| Strict pulse-presence decision | 6/8 → 7/8 | 8/8 → 7/8 |
| Long onset-free gaps | 8/8 → 8/8 | 8/8 → 8/8 |
| Meter/downbeat abstention | 8/8 → 8/8 | 8/8 → 8/8 |
| Independent-source abstention | 8/8 → 8/8 | 8/8 → 8/8 |
| Valid cited IDs and spans | 8/8 → 8/8 | 8/8 → 8/8 |
| Calls, including failed attempts | 39 → 51 | 45 → 59 |
| Failed calls, recovered by retry | 1 → 1 | 0 → 0 |

Both tuned agents returned `null` on stationary noise rather than claiming a regular
pulse. Under the fixed strict decision score, `null` does not earn the expected
`false`, so the aggregate presence score stays 14/16 and Luna's score decreases.
The rate fields correctly remain null. We did not rewrite answers or loosen grading
to conceal this. Uncertainty handling improved in specificity, not every score.

Calls increased from **84 to 110** across the two held-out comparisons. The new tool
reduces manual interval/gap calculations, but this evaluation demonstrates no token,
latency or cost reduction. Exact token usage was not available. Actual retrieved
measurement records were audited against the raw logs, beyond merely checking that
citation IDs existed: all cited records were retrieved in all six evaluated runs.

## What changed and why

- **Separate overlapping frequency channels.** A dominant bright transient could label
  a coincident low attack as a bright object. Independent low/mid/high spectral-flux
  events recover the low component without pretending to separate instruments.
- **Windowed pulse evidence.** `get_rhythm` / `muvi rhythm` returns exact-window rates,
  interval consistency, phase concentration and local timing changes. A global BPM
  no longer has to stand in for every section.
- **Missing-event and quantization handling.** Fit integer-cycle positions across
  attack timestamps. This avoids averaging rests into a slower pulse and avoids
  cumulative phase error from frame-quantized median intervals.
- **Observed events versus hypotheses.** Paged attacks and long gaps are separate from
  the global grid preview, whose unsupported positions are marked `extrapolated`.
  Meter/downbeat and source identity stay unresolved.
- **Agent instructions.** The skill distinguishes band activity, acoustic pulse,
  musical beat and instrument identity, and tells agents to query local windows and
  retrieve evidence. CLI path aliases versus MCP full-ID requirements are explicit.

On the seven periodic held-out signals, detected low-event F1 improves from an average
of 6/7 (one fully masked case) to 1.00 in every case. **Raw detection is not sufficient:**
the noise recording yields 266 candidate low-band changes with no supported pulse.
Its raw event F1 is zero. Consumers must use pulse qualification, not label every
returned change a beat. The old global tempo/grid algorithm itself is not improved
or validated as a general musical beat tracker.

## Verification and reproducible evidence

- 0.5.0: 67 engine/CLI/MCP regression tests passed, plus the separate missing-answer
  scoring regression. All 16 original controlled benchmark fixtures passed.
- The actual SDK exercised the new rhythm tool and retrieved its evidence; CLI tests
  cover paging, invalid spans, old-schema abstention and lazy cached reads.
- Final 0.5.1: all 73 regression tests passed, including actual Windows contention,
  and all 16 controlled benchmark fixtures passed. The independently installed
  core-only wheel passed the public-command smoke test outside the checkout.
- The skill passed `quick_validate.py` and was behaviorally exercised by Luna.
- Both MCP conditions encountered one transient Windows directory-publication error;
  each succeeded on the next attempt. These errors and retries remain in the logs.
  Publication reliability was fixed separately in 0.5.1 with at most five attempts
  and 0.75 seconds of total backoff. A real Windows directory-sharing handle reproduced
  contention and verified recovery; permanent/other failures still propagate.

The rhythm implementation was committed as `239ab99`. The final 0.5.1 package changes
publication behavior and version labels, not perception math. All eight held-out
recordings were reanalyzed: rhythm, tempo, sound objects and evidence measurements
match the evaluated snapshot exactly. See [equivalence results](verification/beat-eval/final-equivalence.json).

Machine-readable [summary](verification/beat-eval/summary.json), individual answers and
scores, generated truth, frozen source hashes, retrieval audits and pipeline metrics
are retained in [the evidence directory](verification/beat-eval).
Raw request/response traces, including errors, are preserved in the
[0.8.3 source download](https://github.com/flrngel/muvi/releases/download/v0.8.3/muvi_genome-0.8.3.tar.gz)
at `docs/verification/beat-eval/tool-traces.zip`. Binary archives are excluded from
Git history. `scripts/beat_cases.py` regenerates audio and truth;
`scripts/score_beat_answers.py` and `scripts/audit_beat_evidence.py` score and audit
answers. The original baseline is commit `301d476`; the evaluated tuned snapshot is
identified by [file hashes](verification/beat-eval/tuned-freeze.json).

Still unvalidated: real-music listening annotations, perceived meter/downbeat,
syncopation/swing semantics, source separation, semantic instrument identity,
probability calibration and comparison with audio-capable LLMs. Research rationale
and primary references are in [BEAT_RESEARCH.md](BEAT_RESEARCH.md).
