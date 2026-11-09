# Real-music beat tracking: evidence and design

2026-11-08. Baseline: package 0.5.2, pipeline 0.5.1, commit b1d083e.

## Causal diagnosis

The three original NCS recordings produced unresolved local acoustic rates in
23/24 fixed low/high-band windows. This was not missing audio: abundant attacks
were detected. `rhythm.pulse_summary` asks whether at least 70% of adjacent event
intervals and their phase support one acoustic pulse. Overlapping kick, snare,
melody and subdivisions violate that assumption. Lowering this threshold would
turn an ambiguous attack stream into an unjustified tempo claim.

`tempo.estimate` selected a global autocorrelation peak, then extrapolated one
constant-period grid through the recording. It never optimized a local sequence
of beat positions. On & On's 69.65 BPM was also a non-octave alias of the stronger
weighted periodicity near 174 BPM. Invincible and Sky High primarily exposed
metrical-level ambiguity (roughly 200/100 and 64/128 BPM).

Independent baseline consumers confirmed the public behavior. Terra additionally
found that 31/32 Invincible grid points were near attacks among 125 low-band events
in one 16-second window. Dense attacks make proximity alone look convincing;
proximity is neither a beat-accuracy score nor a calibrated confidence.

## Technical evidence and implementation

- [Ellis, 2007](https://www.ee.columbia.edu/~dpwe/pubs/Ellis07-beattrack.pdf)
  combines local onset evidence and interval consistency through dynamic programming.
  Muvi implements that general idea independently with NumPy/SciPy; it does not
  claim to reproduce the paper's reported scores or exact algorithm.
- [Fourier tempograms, Müller/Grosche](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C6/C6S2_TempogramFourier.html)
  motivate examining periodicity beyond one autocorrelation maximum. Muvi ranks
  autocorrelation candidates with Fourier fundamental/second-harmonic support and
  an explicit 120 BPM log-normal prior. Scores are uncalibrated ranks.
- [librosa beat tracking](https://librosa.org/doc/main/api/generated/librosa.beat.beat_track.html)
  and its [dynamic tempo example](https://librosa.org/doc/0.10.2/auto_examples/plot_dynamic_beat.html)
  distinguish tempo estimation from sequence tracking. Librosa was consulted as
  a reference; it is not a Muvi dependency and its outputs are not our ground truth.

The tracker balances whole-mixture novelty with normalized low/mid/high flux.
This prevents strong high-frequency subdivisions from erasing slower low-band
periodicity in controlled tests. Eight-second windows with two-second hops guide
a dynamic-programming path. Locally coherent tempo can supply an anchor when
global periodicity smears under gradual change. Local half/double changes use an
explicit metrical prior. Supported points snap to salient attacks within 50 ms;
other path points remain marked `interpolated`. Silence/noise and unsupported
query windows abstain. Neither label establishes musical correctness.

The old acoustic `rhythm` contract is preserved. New `beats`/`get_beats` exposes
the different inference with paging, provenance, alternatives and limitations.
Meter, downbeat and independent bass/instrument identity remain unestimated.

## Community requirements, not technical ground truth

[Discussion of EDM breaks](https://www.reddit.com/r/DSP/comments/1j2vaoj)
motivates explicit unsupported spans rather than blindly presenting a continuing
grid. [Discussion of beat synchronization](https://www.reddit.com/r/deadasdiscothegame/comments/1ta3qr7/anyone_know_a_good_method_or_have_a_tutorial_for/)
motivates checking timestamp/phase accuracy in addition to BPM. These are user
experience reports, not validated labels or algorithmic evidence.

## Reference data

[RWC 2.0 audio](https://zenodo.org/records/17177919) and
[versioned annotations](https://github.com/rwc-music/rwc-annotations)
provide six preselected pop/jazz excerpts for held-out evaluation. The annotation
maintainers document merging AIST and Beat This annotations, sonification, quality
checks and corrections. See [RWC Revisited](https://transactions.ismir.net/articles/10.5334/tismir.326).
Numeric references were first inspected after the source/skill freeze.

These research inputs are CC BY-NC 4.0 and are not distributed in Muvi. Source and
excerpt SHA-256, ZIP CRC, annotation revision/hash, attribution and original excerpt
coordinates are retained. The [predeclared protocol](REAL_BEAT_PLAN.md) fixes the
six cases and strict one-to-one 70 ms scoring before evaluation. No beat-level
human references exist here for the three NCS development songs; their availability
and plausible BPM must not be advertised as measured accuracy.
