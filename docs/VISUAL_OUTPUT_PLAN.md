# Visual output correction — acceptance plan

Baseline: 0.8.1 (`3ef0a08`). The prior visual audit rendered seven real recordings
and one controlled signal. It found an extrapolated tempo grid drawn as rhythm
context, excessive overview markers, missing image legends and wide terminal rows.

## Scope

Keep the CLI, numerical evidence, canonical analysis and optional chart workflow.
Change presentation only; no DSP, dependency, tool or app additions. Ship one patch
release, 0.8.2. Old analysis caches remain usable; chart cache identity must change.

## Verify before accepting

1. Rendered beat coordinates and support classes must equal the stored tracked
   sequence in the half-open requested span. Never extrapolate a legacy grid.
   Old/unresolved tracking explicitly shows unavailable/no tracked hypotheses.
   A controlled silent span must not acquire fabricated markers.
2. Limit individual beat markers and candidate boundary lines for overview
   readability. State omissions/counts in the image and JSON, retain all actual
   coordinates in the legend, and preserve full numerical retrieval.
3. Add a visible digital-power color scale and acoustic object descriptions.
   Keep inference/source-identity limitations visible. Retain the shared original
   time axis, 1600x900 export, track/analysis IDs and exact companion coordinates.
4. Print each flow item's ID and the ending ID. At 80 and 120 columns, wrap prose
   and adapt tables without dropping values, evidence IDs or cross references.
   Treat Unicode display width and untrusted terminal control characters safely.
   Machine JSON must remain unchanged by terminal width.
5. Start with failing regressions for the meaningful semantic/cache/width cases.
   Run targeted CLI/chart/MCP checks, then the full suite once changes stabilize.
   Inspect new whole/detail images for the same eight recordings, including silence,
   against the retained baseline; verify legends and PNG dimensions.
6. Build and smoke-test the installed core wheel outside the checkout; verify
   package metadata, source/skill artifacts and clean up owned helpers. Record
   actual results and limits. A Windows run is not a Mac runtime test.
