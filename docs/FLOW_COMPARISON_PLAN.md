# Fixed evaluation contract: Muvi flow and arbitrary comparisons

Declared before implementation, 2026-11-08. Baseline `ebe5371` / package 0.7.0.
Purpose: original audio -> measured evidence -> compact representation -> LLM
questions, comparison and qualified interpretation. Preserve CPU/local operation,
original coordinates, optional MCP and unresolved source/meter semantics.

## Fixed criteria and release gates

Separate tool correctness from independent consumer reasoning. Do not change these
criteria after seeing held-out answers. Record pass/partial/fail with the offending
claim; no combined "music understanding accuracy" score.

1. **Scope:** exact A/B original-recording bounds, including unequal durations and
   windows crossing candidate boundaries. No enclosing-section substitution.
2. **Arithmetic:** B-minus-A band power and level changes, source RMS and per-band
   attack-rate differences agree with the returned measurements. Count and rate
   have distinct units. A higher fraction alone never establishes higher power.
   Zero power, unavailable frames and null dB must not create infinite/fabricated
   deltas. Tiny displayed rounding differences are scored at half the displayed unit.
3. **Overall:** cover beginning, middle and ending at the actual duration; describe
   acoustic changes, persistence and supported returns. A list of group letters is
   partial, not full understanding. A compact view must disclose omissions and its
   candidate-section basis. Equal group letters alone cannot prove a return.
4. **Activity:** distinguish digitally zero PCM, reduced energy and sustained
   signal with few detected attacks. A boundary-contaminated section mean is not
   a source-silence measurement.
5. **Grounding:** every material numerical/directional claim has compatible track,
   analysis, original span, units and measurements in an actually received response.
   Sufficient inline evidence counts; redundant get_evidence calls are not required.
   IDs alone without supporting returned measurements do not count.
6. **Usefulness and restraint:** answer supported questions; excessive abstention
   is incomplete. Do not assert instruments, independent bass, meter/downbeat,
   semantic section labels or listening without discriminating evidence.

Implementation release requires all deterministic arithmetic/scope/provenance tests,
legacy section-call compatibility, actual CLI and MCP behavior, finite JSON,
bounded overall pagination including the ending, and lightweight cached reads.
Independent acceptance requires each model to answer all requested comparisons and
whole-recording questions; any wrong direction, unsupported material claim, omission
or unhelpful overview is explicitly reported. A consumer miss cannot be relabeled a
tool pass. One bounded correction round is allowed if a reproducible defect remains;
if used, retain the first answer and use fresh agents/new inputs for confirmation.

## Evaluation sequence

- Reuse prior 0.7.0 failures as development evidence: a reversed high-attack
  comparison, shallow overall accounts and unnecessary evidence-fetch requirements.
  Use existing controlled inputs only for development; no new beat-DSP tuning.
- Add meaningful property/behavior tests first: reversal and identity, gain changes,
  unequal-duration normalization, silence vs missing frames, all-track flow coverage,
  sustained energy, group-label collisions, recurrence with absolute-level checking,
  bounded pages and inline provenance. Use independent arithmetic/construction.
- Extend existing `compare`/`compare_sections` and `inspect`/`get_track_digest`;
  no new public tool. Keep the skill concise using the skill-creator guidance.
- Freeze runtime and skill before held-out analysis/consumer evaluation. Two new
  complete recordings: Different Heaven & EH!DE **My Heart** and Disfigure **Blank**
  from official NCS public downloads; if a download is unavailable, record that
  failure and choose an official accessible replacement before inspecting outputs.
  Use neutral filenames and original MP3 coordinates, not YouTube timestamps.
- Also generate one new anonymous arrangement after freezing: reordered material,
  level-only variation, sustained energy, silence and a return. Its construction
  provides reference truth; real songs supply grounding checks, not perceptual truth.
- Fresh `gpt-6.1-terra` and `gpt-6-luna` agents independently receive only the frozen
  skill, installed/public commands and natural questions. No source, truth, old
  answers, suspected failures or communication between them. Preserve actual calls,
  stdout/stderr, answers and wrapper failures. At least one uses actual MCP.
- Query three deterministic nonaligned spans per real recording: [13.25,29.75),
  [61.125,84.375), [121.75,138.25), plus full-duration overview. Compare A->B and
  B->C; describe whether the last span resembles an earlier one with qualifications.
- Root audits arithmetic, provenance and semantic claims against raw responses,
  section measurements and construction. Tool counts/context size are descriptive;
  no speed ranking or general accuracy claim. Report every case, including failures.
- Run full regression suite with MCP, installed-wheel smoke, schema/skill/lint/lock
  checks, package/source/skill archive validation and macOS dependency preflight.
  Bump package to 0.8.0, retain pipeline 0.6.0, commit and clean owned helpers.

## Research basis

Code and retained independent traces establish the specific workflow failures.
[Müller's FMP discussion](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C4/C4S1_MusicStructureGeneral.html)
separates repetition, homogeneity and novelty: flow should expose measured change
and qualified similarity, not equate one segmentation/grouping with musical form.
[A community audio-analysis account](https://www.reddit.com/r/udiomusic/comments/1hsaiq8/interesting_use_case_with_gemini_experimental/)
motivates testing invented properties and temporal spillover; it is anecdotal and
supplies no algorithm guarantee/reference truth. No third-party algorithm copied.

## Declared bounded confirmation after round one

Round one used the frozen 0.8.0 candidate and all originally named inputs. Tool
arithmetic and complete retrieval passed for both agents, but Luna broadened a
flow statistic's time span and generalized similar energy/overall attack rate to
all measured statistics despite a different mid-band rate. Terra's silence wording
also blurred zero power versus null dB. Preserve these answers and the criteria above.

Use the single allowed correction: expose a deterministic, scoped comparison
synopsis (including every band rate) in the existing response, plus a short skill
instruction to preserve statistical bounds when compressing prose. No new API or
DSP. Package 0.8.1 records this completed fix separately from feature commit 0c61096.
Freeze again before analyzing two new official recordings: Janji/Johnning **Heroes
Tonight** (`https://ncs.io/ht`) and Cartoon/Jéja/Coleman Trapp **Why We Lose**
(`https://ncs.io/whywelose`). Use the same predeclared real-song intervals. A new
48-second arrangement reorders sustained mid, opening low/high, quiet pulses,
silence, stronger pulses and opening return. Fresh Terra CLI/Luna MCP consumers get
only public questions and the final skill; no first-round answers or feedback.
Report residual misses without further tuning on this confirmation set.
