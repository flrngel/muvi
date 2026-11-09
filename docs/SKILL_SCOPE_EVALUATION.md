# Overall and interval understanding — Muvi 0.7.0

2026-11-08. The objective was useful, grounded understanding of an entire recording
and arbitrary intervals, with the smallest justified implementation. The beat DSP
was not retuned. This is a behavioral skill/tool evaluation, not a claim that a model
heard the recording or achieved general musical intelligence.

## What was actually needed

Fresh baseline Terra and Luna consumers used 0.6.0 and its existing skill. Both
covered the whole development tracks when they read every section, but neither
could retrieve exact-interval band power. They had to qualify enclosing-section
statistics as broader context. Null source peak/RMS also left the silent interval
unresolved even though the decoder had measured all-zero PCM.

The implementation therefore adds **one tool**, `window` / `get_window`, combining
existing source activity, band energy, brightness/texture and compact rhythm.
It defaults to the whole track or accepts exact requested bounds. Derived `W…`
evidence can be retrieved at those bounds. Existing digest sections gained paging
for MCP; CLI `sections` already listed all sections. Source-level nulls now explicitly
say `digital_silence` rather than leaving their meaning ambiguous.

The skill now routes overall → exact interval → comparison, differentiates absolute
power from band fractions, avoids exhaustive event retrieval for summary questions,
and requires relevant evidence. No new model, dependency, UI, source separation,
semantic classifier or second comparison API was added. Existing comparisons still
operate on stored section boundaries; arbitrary comparisons use two window queries.

## Verification before implementation

[The plan](SKILL_SCOPE_PLAN.md) preceded changes. Baseline source/skill was commit
`d30112e` / 0.6.0. Initial tuning used anonymous synthesis c17 and the existing
official NCS On & On recording. c17's physical construction has successive low
pulses, enriched low/high material, sustained mid/high material, returning low
pulses and silence. User intervals were deliberately inside, but not aligned with,
detected sections. Models saw no generator, truth, implementation or each other's work.

Code and the first revised skill were frozen before a reordered 45-second c42
synthesis and Sky High were queried. Fresh `gpt-6.1-terra` and `gpt-6-luna` agents
answered four cases each, including the development cases for comparison. Both
chose actual CLI calls; actual MCP window/evidence behavior was separately exercised
by the integration test, not misreported as independent model MCP use.

## First forward test: numbers passed, an overall answer failed

Both agents returned **16/16 numerically matching exact windows**, with retrieved
query evidence. Both correctly calculated the six synthetic interval comparisons,
identified active C and silent D windows, and matched returning material. The
comparison distinguishes an important trap: c17 A→B low power rises 5.832 dB and
high power 39.537 dB while mid power is nearly unchanged (+0.003 dB). Wider section
means make mid energy appear to rise because their boundaries include other material.

Terra's overall accounts covered all four recordings. **Luna failed c42's overall
account**: its numeric fields correctly said 45 seconds, but its paragraph copied
the 40-second c17 progression and 120/240 BPM wording. The actual c42 order and local
rate differ. Successful retrieval and arithmetic did not establish narrative understanding.
The original wrong answer is retained; it was not silently corrected or counted as a pass.

The first wrappers also mishandled UTF-8 on Windows: Terra recorded one decoding
failure/retry; Luna recorded ten. Luna additionally corrected a list/dict shape error
in its own harness. These are consumer-wrapper failures, not successful Muvi captures.
Baseline traces have disclosed gaps for initial help/progress-only captures; counts
are descriptive and cannot support a controlled speed or model-ranking claim.

## Minimal second tuning and fresh confirmation

Only the skill changed after that failure: it now specifies UTF-8 for Python
subprocess wrappers and checks each overall paragraph's duration, first/last passage,
change order and tempo against **that track's** evidence. It permits reuse of answer
format, not reuse of another recording's narrative. Runtime bytes remained frozen.

A second freeze preceded a new 35-second c58 arrangement and a different real track,
Invincible. c58 changes the order to enriched low/high → silence → low pulses →
mid/high → enriched low/high; the returning window matches B, not A. Previously used
c42 was retained as a regression case. Two new agents received the final skill and
these three user requests without old answers, reference truth or the known failure.
Only c58 and Invincible are new cases in this round; c42 is not relabeled held out.

The final audit compares reported values with the agents' **actual CLI responses**,
not with what their debriefs claimed. Both agents' packets exactly match the root
reference for all 13 windows. Their canonical genomes also match except elapsed
time. This isolates the remaining mistakes to answer construction.

| Final confirmation | Terra | Luna |
| --- | --- | --- |
| Correct duration and chronological coverage | 3/3 | 3/3; synthetic descriptions partly just group/range lists |
| Returning material: c58 matches B, c42 matches A | 2/2 | 2/2 |
| Synthetic comparison direction and active/silent distinction | 6/6 | 6/6 |
| Exact requested windows, with retrieved `W` evidence | 13/13 | 13/13 |
| Structured numeric windows match at displayed precision | 13/13 | 12/13 |
| All cited overall evidence actually fetched with `evidence` | 3/3 | 0/3; summaries were read, but cited `E` records were not fetched |

The cross-track 40-second narrative did not recur. Both used the new 35-second
arrangement and the 45-second regression case correctly, and covered Invincible
through its actual 273.072-second ending. Neither final trace contains the earlier
UTF-8 decoding failure. Terra retained a failed initial `python -m muvi` discovery
attempt before using the documented executable; Luna split an analysis loop after
an outer command timeout. Retained successful calls number 28 and 35 respectively;
these are descriptive counts, not performance benchmarks.

Residual errors are retained, not rounded into a perfect score:

- Terra's Invincible prose says the last window has fewer attacks in *each* band
  than the first. Its own table shows high attacks **128 → 130**, while low/mid
  decline. Its c58 low-power delta is approximately 6.5 dB from rounded values;
  the unrounded delta is 6.4368 dB. The qualitative synthetic comparisons are correct.
- Luna copied two c42 B powers incorrectly: low -16.4198 instead of -16.4185857,
  and high -38.0058 instead of -38.0050249 dB. These tiny transcription errors do
  not reverse the conclusions, but exceed its displayed four-decimal rounding.
- Luna's synthetic overall accounts give correct groups/times but only partial
  acoustic progression; “A-like” is ambiguous between a requested window and a
  detector group. It also cites overall `E` IDs without retrieving their evidence
  records, despite reading the corresponding digest/section summaries. Its claim
  that all cited **W** records were retrieved is true; that is narrower than full
  citation compliance.

[Item-level semantic judgments](verification/skill-scope/final-semantics.json),
[Terra's numerical audit](verification/skill-scope/final-terra-audit.json) and
[Luna's numerical audit](verification/skill-scope/final-luna-audit.json) separate
these outcomes. Unedited final answers are saved beside the audits. No additional
API or model was added to hide these consumer errors. One skill-only correction
and fresh confirmation were sufficient to test the main routing/scope improvement;
they do not prove error-free model reasoning.

## Remaining limits and interpretation

- Section groups are approximate descriptors. In c42 two candidate sections share
  group C even though the requested inner windows are silent versus energetic.
  Exact interval measurements must take precedence over group labels as evidence
  of repetition. Broad detector boundaries do not establish verse/chorus function.
- Spectral means use cached frame centers in the requested half-open interval;
  STFT context can extend up to 0.186 seconds beyond a center. Source RMS/activity
  uses rounded original-sample bounds. Sub-frame intervals can have no spectral
  samples while still containing source audio.
- Real-song checks establish full-duration coverage, correct use of returned
  measurements and retrieved citations. There are no new human arrangement labels
  or beat annotations here. [The earlier beat accuracy limits](REAL_BEAT_EVALUATION.md)
  still apply, including half-tempo and phase errors. No new beat accuracy gain is claimed.
- These are small procedural blind tests and root-reviewed semantic judgments,
  not statistical estimates, calibrated confidence or raw-audio model comparisons.

## Evidence, research and reproducibility

The implementation choice follows the inspected code and independent failures.
[Müller's music-structure discussion](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C4/C4S1_MusicStructureGeneral.html)
distinguishes contrast, repetition and homogeneity and explains why one acoustic
segmentation cannot establish every musical relationship. A
[community audio-analysis report](https://www.reddit.com/r/udiomusic/comments/1hsaiq8/interesting_use_case_with_gemini_experimental/)
describes invented attributes and timestamp spillover; it motivated exact spans
and neutral filenames, but supplied no reference truth or algorithmic guarantee.

Local raw inputs, constructors/truth, frozen code/skills, every retained call,
unmodified answers and audit scripts are in `artifacts/skill-scope/`. Public compact
verification records, including the original final answers and first-round failure
excerpt, are under `docs/verification/skill-scope/`. Synthesis is original;
NCS audio is reused from the preceding examples and is not distributed with Muvi.
Window IDs are scoped by track and analysis: the same time range on different tracks
can have the same short ID, so citations retain all three identities.

The final reusable skill is [skills/muvi/SKILL.md](../skills/muvi/SKILL.md), also
available as `dist/muvi-skill-0.7.0.zip`. Package 0.7.0 reuses pipeline 0.6.0 and
schema 0.3.0. [Verification](VERIFICATION.md) records tests and installation checks.
