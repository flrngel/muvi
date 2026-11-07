# Rhythm evaluation research notes

Checked 2026-11-06. Primary research, local code and direct consumer observations
drive implementation; community discussion identifies pain points, not ground truth.

- [Müller / Ellis, beat tracking by dynamic programming](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C6/C6S3_BeatTracking.html):
  a beat tracker combines onset evidence and timing assumptions. A constant-tempo
  lattice is a hypothesis and can disagree with observed events or tempo changes.
- [Müller / Grosche, Fourier tempograms](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C6/C6S2_TempogramFourier.html):
  local periodicity is a time-varying quantity. The implementation here exposes local
  inter-onset consistency; it does not claim to reproduce the Fourier tempogram method.
- [mir_eval beat evaluation and Davies et al.](https://mir-eval.readthedocs.io/latest/api/beat.html):
  timing and continuity require reference timestamps, and metrical levels can be
  ambiguous. Our controlled corpus asks about physical low-transient pulse intervals,
  so the preregistered rate metric does not forgive half/double answers. It is not a
  standard perceptual beat leaderboard or a subjective musical-meter annotation.
- [Community BPM detector discussion](https://www.reddit.com/r/audioengineering/comments/196ysgu/bpm_detection_algorithm_help/):
  users report difficulty moving from loop-duration shortcuts to groove detection.
  We use this as motivation for transparent evidence and ambiguity, not as a verified
  technical claim or permission to assume 4/4.
- Local code inspection: 0.4.0 creates one global autocorrelation tempo, a constant
  extrapolated grid, and one descriptor cluster per composite onset. It exposes
  occurrence lists but no bounded rhythm/local-rate/gap retrieval tool.
- Direct black-box evidence: Terra independently found changing local rates hidden by
  the global estimate and had to calculate a long gap from occurrences. The root's
  controlled development check found strong coincident high-frequency attacks can
  mask the low role in that single-object clustering. Both warrant a separate
  per-band event channel, without claiming separated instruments.

No new pretrained model, music download, external model API or model-weight license
assumption is needed. Held-out synthesis is kept separate from tuning.
