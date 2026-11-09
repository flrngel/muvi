# Exact comparisons and acoustic progression — Muvi 0.8.1

The [evaluation contract](FLOW_COMPARISON_PLAN.md) was committed as `14e048a`
before implementation. Baseline: `ebe5371` / 0.7.0. Feature commit: `0c61096` /
0.8.0. The criteria distinguish arithmetic, scope, useful acoustic explanation,
activity, sufficient received provenance and unsupported claims. Successful tool
calls are not treated as successful musical reasoning.

## Smallest implemented change

Two existing entry points were extended; tool count remains 15 typed/16 MCP:

- `compare TRACK --a START END --b START END` and MCP `compare_sections` with
  `range_a`/`range_b` return computed B-minus-A absolute band energy, RMS, texture
  and normalized per-band attack-rate changes, with exact input `W` evidence inline.
  Zero and unavailable measurements retain separate semantics. Section-ID calls
  remain compatible. No separate arbitrary-comparison tool was added.
- `inspect` / `get_track_digest` adds `flow`: measured acoustic progression from
  stored candidate sections, with changes, qualified returns and an explicit final
  item. Consecutive similar observations are aggregated; gradual drift is not
  collapsed through pairwise chaining. Pages contain at most 12 items. The method,
  heuristic thresholds, units and underlying evidence references are explicit.

The 0.8.1 correction adds a deterministic comparison synopsis exposing every band's
rate alongside the exact A/B bounds. Its short skill additions preserve statistical
bounds when compressing prose and distinguish similar energy from similar rhythm.
No new DSP, model, dependency, UI or source labels were introduced. Package 0.8.1
keeps extraction pipeline 0.6.0 and canonical schema 0.3.0; no reanalysis is needed.

## Independent use and first-round failures

Each round used fresh `gpt-6.1-terra` via the installed CLI and `gpt-6-luna` via an
actual MCP stdio client. Agents saw only the frozen skill, neutral audio paths,
natural questions and public responses. They did not see source, construction,
references, old answers or each other. Transport and at least one comparison call
per requested pair were prescribed; other queries were their choice. This is not
an unconstrained tool-selection benchmark or a model-ranking experiment.

The first freeze preceded two new complete official downloads,
[My Heart](https://ncs.io/myheart) and [Blank](https://ncs.io/blank), plus original
39-second construction c83. Exact real-song ranges were declared before analysis:
[13.25,29.75), [61.125,84.375), [121.75,138.25). Their unequal durations make count
versus rate an observable distinction. c83 tests gain-only variation, sustained
mid energy with no detected attacks, digital silence and a returning construction.

Both agents received every flow page (15/9/6 items) and all seven requested
comparison packets. Root verified all 14 packets exactly against independent
retrieval and recomputed dB/rate arithmetic from their operands. Terra preserved
all seven structured comparisons exactly. Its trace contains 15 successful CLI
calls; Luna's contains 26 successful MCP calls, including 12 extra window queries.
These counts are descriptive. Terra reported an unavailable initial Python launcher;
Luna reported SDK timeout/serialization harness failures before its successful log.
Those startup attempts are not misrepresented as fully captured successful calls.

Useful explanations improved over the earlier group-list accounts, but failures
were retained:

- Luna applied the strong 33.37–120.05 s flow item's −0.3 dB / 4.91 attacks/s to
  an expanded 27.5–120.0 s passage, which also contains a weaker transition.
- Luna called O/R nearly identical in all measured statistics, while detected
  mid-band rate changes 1.778 → 2.444/s. Similar power and overall rate did not
  establish similarity of every band rate.
- Terra correctly identified source silence but called its spectral power “null”;
  the returned linear powers are zero and their dB levels are null. Its structured
  observations preserve that distinction, so this is a prose-precision miss.

The single correction allowed by the original plan addressed representation and
scope, then was frozen again. No first-round answer was rewritten.

## Fresh confirmation

Confirmation uses two different complete official downloads,
[Heroes Tonight](https://ncs.io/ht) and [Why We Lose](https://ncs.io/whywelose), plus
new 48-second construction c93. Its block order and frequencies differ; the returning
low/high material first occurs in the second block. The same fixed criteria apply.
New agents received no first-round feedback. Root independently audited their
unchanged answers and actual responses against the fixed criteria.

| Final check | Terra (CLI) | Luna (MCP) |
| --- | --- | --- |
| Required exact comparison responses match reference and independent arithmetic | 7/7 | 7/7 |
| Complete flow items actually received | 18/15/6 | 18/15/6 |
| Requested comparison energy and per-band rate conclusions | 7/7 supported | 7/7 supported |
| Whole-recording duration, chronology and acoustic explanation | 3/3 supported | All three covered; two real-song accounts have errors below |
| Sustained C vs digital silence D; gain vs relative balance | Correct | Correct |

Terra's structured observations exactly match all seven requested comparisons and
two additional A-to-C comparisons. Its 15 logged CLI calls succeeded. Luna's 30
retained MCP calls succeeded; the agent reported that a retry overwrote its initial
failed `audio_path`-instead-of-`path` call. This trace gap is retained as a limitation,
not claimed to be a complete error-free history. Its seven structured evidence
packets, 21 quoted band-power changes and 42 per-band rate operands were checked
against returned values at displayed precision, separately from its overall prose.

The final gain-only comparison was useful: both models reported roughly −6.02 dB
in all bands, unchanged relative balance/overall rate, **and** a decreased mid-band
detection rate (4.792 → 3.125/s). Both described source-active sustained C with no
detected attacks and exactly zero PCM in D. Neither substituted section means for
these exact comparisons. Terra's silence wording now distinguishes zero linear
power from a null dB difference.

Remaining final Luna misses:

- It calls `FLOW_012` the ending for both real recordings. The actual final items
  are `FLOW_018` (Heroes Tonight) and `FLOW_015` (Why We Lose). Its ending duration
  and descriptive statistics came from the final pages, but the navigation references
  are wrong. Flow IDs are not independently retrievable evidence IDs.
- For Why We Lose's 87.946–130.670 s passage it says all bands increase. Relative
  to the previous 76.475–87.946 s item, **mid power falls 0.03411 → 0.02564** while
  low and high rise. The exact requested comparison answers correctly distinguish
  individual band changes; this separate overall sentence still fails grounding.

These are partial semantic outcomes, not a claim of perfect musical understanding.
No additional tuning was performed on the final confirmation set. The compact
[semantic judgments](verification/flow-comparison/semantics.json) and unedited
answers distinguish correct observations, useful explanation and remaining misses.

## Interpretation and remaining limits

- Acoustic flow is a query-layer view of approximate detector sections. It cannot
  establish song form, source silence, instrument identity or identical phrases.
  A cropped portion of a flow item has not automatically inherited that item's
  measured statistics. Exact comparison/window queries remain available.
- Flow recurrence is conservative. In c83, exact O/R windows strongly resemble
  each other, but the broader section means do not trigger `similar_to`. Boundary
  context and very low-energy bands can prevent a match. Absence of a match is
  not proof of different musical material.
- Existing attack detection is not gain/phase invariant: c83's half-amplitude copy
  preserves the constructed rhythm but loses some mid-band detections; repeated
  material also yields different mid-band counts. The new comparison faithfully
  exposes these detector outputs. It does not convert attacks into true musical beats.
- Real-song checks verify grounding in received observations. They do not supply
  human arrangement annotations, listening tests or new beat accuracy. Four NCS
  electronic recordings do not establish genre-wide performance. The earlier
  [beat-tracker limits](REAL_BEAT_EVALUATION.md) remain applicable.
- Inline evidence counts when it includes compatible measurements, original bounds,
  units, method and track/analysis identity. Repeating an evidence fetch is not a
  success metric; missing supporting detail still requires retrieval.

## Verification and reproducibility

The tests preceded implementation. Six new tests cover gain/reversal/identity,
zero vs unavailable frames, independent rate normalization with opposing band
directions, sustained activity, group-label collisions, drift, full-flow pagination,
CLI validation, inline evidence and cached reads without numerical imports.
Existing actual MCP integration also exercises range comparisons and flow.
The 0.8.0 full suite passed **96 tests in 391.11 s**. The final 0.8.1 full suite passed
**96 tests in 363.83 s**, including actual MCP. Installed core-wheel smoke, eight
macOS binary-dependency resolutions, frozen-file/wheel-module equivalence and skill
validation are recorded in [verification](VERIFICATION.md). No physical Mac runtime
test was performed. No elapsed-time comparison is claimed under concurrent workloads.

Local raw calls, inputs, construction, reference retrieval and audit scripts are
under `artifacts/flow-comparison/` and `artifacts/flow-confirmation/`. Public compact
records and unedited answers are in `docs/verification/flow-comparison/`. Audio is
not bundled. Source manifests retain original download URLs, hashes and duration;
MP3 times do not claim alignment with YouTube playback. Music provided by
NoCopyrightSounds; individual official pages above supply artist attribution.

Code and retained failures drove the implementation. The plan cites the primary
FMP structure discussion (repetition/contrast/homogeneity are distinct) and a
community report as motivation only. Neither validates this architecture or
supplies the test reference answers.
