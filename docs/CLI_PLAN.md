# CLI-only conversion: verification contract

## Requested outcome

Replace the browser application completely with a terminal product. Preserve measured
music evidence, local audio retention, cache reuse, exports, and optional stdio MCP.
Release this breaking interface change as 0.4.0. Existing libraries remain readable.

## Design

- Direct commands for analysis, inspection, sections, sound search/details, evidence,
  comparison, hypothesis checks, metrics, original crops, charts, canonical export,
  demo generation, tool/schema discovery, benchmarks and MCP configuration.
- Human-readable default output; explicit `--json` for one machine-readable stdout
  document. Progress and diagnostics go to stderr. `--quiet` suppresses progress.
- Audio paths and unambiguous track-ID prefixes avoid repeatedly copying full hashes.
  `latest` explicitly means the newest completed library analysis.
- Accept seconds or `MM:SS`/`HH:MM:SS` intervals. Reject invalid spans and ambiguity.
- Never silently overwrite an export. `--force` is explicit; cache artifacts and
  source audio remain protected even with `--force`.
- Remove HTTP service, static assets, browser launcher, playback-copy generation,
  and direct web dependencies. MCP is an optional extra; the default package runs
  without FastAPI, Uvicorn, Starlette or an MCP SDK installed.

## Verification specified before implementation

1. Keep all applicable DSP, provenance, cache, crop, chart, abstention and MCP tests.
   Replace HTTP tests with real CLI subprocess integration tests.
2. Exercise demo/analyze -> inspect -> sections/sounds/evidence -> compare/verify/metrics
   -> crop/render/export, through both human and JSON output and paths with spaces/Unicode.
3. Verify stdout is parseable JSON with no progress text, including failure paths;
   stdin/JSON-file tool arguments; flags before/after commands; exit codes; malformed
   timestamps, missing files, unknown/ambiguous IDs, and overwrite protection.
4. Verify no browser module, HTTP route, static asset or app launcher is shipped.
   Validate help/version without importing DSP or MCP dependencies.
5. Build and install the wheel outside the checkout into an isolated core-only
   environment; run analysis and exports there. Separately verify MCP with its extra.
6. Re-run controlled fixtures because the pipeline artifact layout changes. Record
   actual results and retain prior scientific limitations. Stop all test subprocesses.
