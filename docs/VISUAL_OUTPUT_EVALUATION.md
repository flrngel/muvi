# Visual output correction — 0.8.2

The [acceptance plan](VISUAL_OUTPUT_PLAN.md) was committed before implementation
as `d4c3153`. Baseline: `3ef0a08` / 0.8.1. This changes presentation only. All 21
other Python modules are unchanged; pipeline 0.6.0, schema 0.3.0 and the numerical
CLI/MCP contracts remain intact. No new dependency, model, tool or app was added.

| Finding | Implemented correction |
| --- | --- |
| Legacy constant-tempo grid looked like tracked timing | Use stored tracked times in the requested half-open interval; green solid marks have onset support, amber dashed marks are interpolated |
| Dense full-track grid hid onset detail | Omit individual marks above 30 seconds or 64 beats; show the count and preserve every coordinate/support in JSON |
| Section lines crossed every panel | Draw only in the object panel; omit above 24 boundaries and disclose the count |
| Spectrogram lacked a scale; object IDs lacked meaning | Visible digital-power color bar and ID-plus-description labels; source identity remains unresolved |
| Flow references had no visible row IDs | Show every row's `FLOW_…` ID and the explicit ending ID |
| Long terminal rows overflowed | Wrap table cells/prose by display width, including CJK and combining accents; preserve values and leave JSON independent of width |

Chart cache identity is now `tile-v2`. Older images are preserved; corrected
images use the same canonical analysis and require no audio reanalysis. The PNG
remains 1600×900. Legends include display limits, omitted coordinates, object
names, source/analysis identity and original time bounds. The thresholds control
visual density only; they are not musical or perceptual thresholds.

## Verification

- Seven new parametrized regression cases failed against the baseline before
  implementation. They cover actual plotted coordinates/support, legacy/missing
  tracking, overview omissions, old-cache preservation, legends and Unicode/flow
  references. Existing CLI tests also verify JSON equality at 80 and 120 columns.
- Full suite: **103 passed in 269.55 s**, including actual MCP. After moving the
  beat legend outside the plot to avoid hiding marks, all affected chart/CLI/MCP
  checks ran again: **10 passed in 58.91 s**. Timings are not performance claims.
- Same visual set as the audit: On & On, Invincible, Sky High, My Heart, Blank,
  Heroes Tonight, Why We Lose and controlled c93. Whole-track and detail views
  produced **16 verified images**. Every beat coordinate/support, boundary and
  object label exactly matches canonical JSON. Original images remain unchanged.
  Final galleries and representative full-size detail images were visually inspected.
- **20 real CLI runs**: inspect, continuation, comparison, window, sections,
  sounds, beats, rhythm, metrics and library list at both 80 and 120 columns.
  Every line fits. The 80-column flow rows and ending retain their IDs.
- Installed core-only 0.8.2 wheel passed smoke outside the checkout, including
  chart legend equality with `beats`, analysis, windows, comparisons, flow,
  evidence, crop/export, configuration and the expected missing-MCP-extra error.
  The 24 packaged Python modules match the working source exactly.
- Ruff, lock and whitespace checks pass. Physical Mac runtime remains untested;
  the dependencies and supported Python versions are unchanged.

Machine-readable results and hashes: [visual-output.json](verification/visual-output.json).
Local before-images are in `artifacts/visual-review/`; final images, logs and
audits are in `artifacts/visual-improvement/`. No audio is included in the visual ZIP.

## Interpretation limits

The c93 silent passage still contains **stored interpolated beat hypotheses**.
The renderer exposes them in amber instead of inventing a regular green grid or
silently discarding them. They do not establish a sound event. Supported timing
is also an inference, not beat ground truth. The detector itself was not retuned.

Whole-track charts deliberately omit individual markers at high density; consult
the retained JSON or zoom for exact timing. Acoustic object descriptions are not
instrument labels. Overall flow and exact A/B comparisons remain text/JSON views;
this change does not add separate diagrams or a graphical application.
