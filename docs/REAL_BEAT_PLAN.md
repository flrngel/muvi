# Real-music beat tracking: verification before implementation

2026-11-08. Baseline: b1d083e / CLI 0.5.2 / pipeline 0.5.1. Development audio is
the three official NCS MP3s from td#842: On & On, Invincible and Sky High. Preserve
their hashes and all original failures. Root owns implementation and scoring; fresh
Terra and Luna consumers independently use only public commands/docs, never source,
reference annotations, external song tempo labels or each other's answers.

## Diagnose before changing behavior

Measure event interval distributions, strengths, global autocorrelation candidates
and rejected window scores. Test causality by comparing binary event timing with
weighted onset envelopes, multiple periodicity candidates and an onset-supported
beat sequence. Event repetition and perceptual beat tracking must be separate fields;
do not replace a null with a guessed BPM or relabel subdivisions as musical beats.

Use primary MIR papers/docs and actual code as technical evidence. Community reports
motivate practical requirements (breaks, subdivisions), not algorithmic truth.

## Development and negatives

- Keep the original fixed 0–16, 32–48, 64–80 and 96–112 second band queries.
- Also evaluate mixture beat tracking in fixed 32–48, 64–80 and 96–112 windows.
  These songs have no manual beat labels here: report coverage and agreement with
  supporting attacks/tempo hypotheses, not ground-truth beat accuracy.
- Preserve existing controlled acoustic-pulse semantics/tests. Add meaningful
  mixture/subdivision, missing events, noise/silence, tempo-change, timing-offset and
  unsupported-gap cases. Beat hypotheses must identify unsupported/interpolated points.
- Preserve bounded JSON paging, evidence retrieval, legacy schemas, lazy cached reads,
  CLI and actual MCP. Version algorithm/parameters; build and test an installed wheel.

## Hold-out real music, selected before results

Use six RWC 2.0 recordings with public reference beat annotations: **P001, P011, P021,
J001, J011, J021**. These deterministic convenience samples span pop and jazz; they
do not represent the entire corpus. Take original-time [30,75) second excerpts. Use
the dataset's documented annotation/audio alignment; retain source IDs/hashes and
attribution. Do not inspect beat values or analyze held-out audio until production
code, parameters and skill instructions are frozen. Downloading files or reading
format/alignment metadata is allowed beforehand. If a selected recording is unavailable,
record that fact rather than silently substitute a favorable case.

Primary metric: one-to-one beat F1 at **70 ms**, using the supplied metrical level
without half/double credit, over [5,45) seconds of each excerpt (exclude startup).
Also report precision/recall, median matched timing error, octave-aware and strict
tempo error, coverage and each individual case. Report baseline and tuned results.
Secondary half/double-tolerant interpretations cannot conceal primary failures.
Noise/silence must not gain a claimed beat sequence. Improvement in tool confidence
alone does not establish accuracy. Compare the actual predicted sequence, not a
post-hoc shifted/rescaled sequence or hand-picked excerpt.

## Independent agent acceptance and final verification

After freeze, give each agent the same anonymized files and fixed questions through
its own library. Preserve raw calls/answers and test actual evidence retrieval.
Use recorded baseline/tuned development answers plus held-out tuned answers; do not
claim randomized experiments or statistical significance from two trajectories.
Ask about tracked beat times, local tempo, subdivisions, gaps, meter and independent
source identity. Scores must distinguish what the tool measured from model guesses.

Keep the freeze intact during held-out evaluation. Report failures and limitations;
do not tune on these references and still call them held out. Run regression tests,
controlled benchmark, MCP and independent installed-wheel smoke checks. Check Mac
dependency resolution if dependencies change. Commit completed implementations with
Conventional Commits, update README/skill/verification, and clean up processes.

No recordings are bundled into the package. RWC audio/annotations remain local
evaluation inputs with their upstream licensing and attribution preserved. No manual
listening or human annotation is claimed unless actually performed.
