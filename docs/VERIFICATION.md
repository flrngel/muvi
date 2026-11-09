# Muvi verification

## 0.6.0 real-music beat tracking

The [predeclared plan](REAL_BEAT_PLAN.md), [research](REAL_BEAT_RESEARCH.md) and
[full real-music results](REAL_BEAT_EVALUATION.md) distinguish inferred beat timing
from the unchanged acoustic attack/pulse contract.

- 83 regression/feature tests passed in 305.12 seconds, including actual MCP,
  cached reads without numerical imports, CLI paging/errors, legacy schemas,
  evidence references and source-time invariants. A separately added reference
  scorer test also passed: **84 tests total**.
- Ten beat feature tests include strong subdivisions, swing, gradual drift,
  a 96→144 BPM change, missing attacks, a silent break, noise/silence abstention,
  schema integrity and real subprocess CLI usage. Actual event F1 is at least
  0.90 on the five positive timing cases, with median error below 20 ms. Missing
  events remain explicitly interpolated; the silent query window abstains.
- All 16 existing controlled benchmark cases pass the original five gates.
- Six held-out RWC reference excerpts yield macro strict F1 0.551→0.674 at 70 ms.
  P001 and J021 regress; all cases and failures are retained. Code/skill were frozen
  before reference inspection and were not tuned on these outcomes.
- Terra independently reproduced match counts/F1 using a different matching
  implementation, checked all six annotation hashes, and confirmed exact agreement
  between its MCP responses and the scored exports. Both models' interpretation
  tests are separate from reference accuracy; neither constitutes listening.
- `ruff check genome tests scripts`, lock validation, and skill validation passed.
  No runtime dependency was added; package and pipeline are 0.6.0, schema 0.3.0.

- Built the 0.6.0 wheel and source archive; installed the wheel with `uv tool install`.
  Both standalone command names report 0.6.0. The core-only smoke test passed outside
  the checkout, covering audio analysis, beat paging/evidence, crop/chart/export,
  schema, MCP configuration and the expected missing-extra error.
- All frozen runtime modules and the skill match their pre-evaluation hashes.
  Wheel module bytes exactly match the checkout. No audio or static app is bundled.
- Binary-only macOS 13 dependency resolution passed **8/8** combinations: Apple
  Silicon/Intel × Python 3.12/3.13 × core/MCP. **No physical Mac execution was tested.**
  [Release checks](verification/real-beats/release-checks.json) retain commands and outputs.
- The [consumer trace audit](verification/real-beats/consumers.json) confirms both
  Terra and Luna covered all 9 tracks / 33 windows, paged every beat, matched the
  scored output exactly, retrieved cited evidence and preserved meter/source abstentions.

These entries supersede the historical release results below where applicable.

## 0.5.2 installation documentation follow-up

README installation, CLI/skill/MCP setup and troubleshooting were reorganized, with
detailed scripting contracts moved to [CLI_REFERENCE.md](CLI_REFERENCE.md). Package
metadata was bumped to 0.5.2; the analysis pipeline remains 0.5.1. No DSP code changed.

- Binary-only dependency resolution passed for macOS 13, Apple Silicon/Intel,
  Python 3.12/3.13 and core/MCP: all eight combinations. Commands and outputs are
  in [macos-install.json](verification/macos-install.json). These checks ran from
  Windows; they do not establish native loading or runtime behavior on a Mac.
- The current locked MCP dependency `cryptography==50.0.2` has no usable Intel Mac
  wheel. Unlocked installation with source builds disabled for that package selects
  48.0.1. The documented standalone MCP command applies this restriction. The same
  source-package resolution was checked with the pip interface's equivalent
  `--only-binary cryptography` flag.
- Built the 0.5.2 wheel and source archive. Verified local documentation links,
  package version and wheel README. Installed the core wheel independently and
  passed `scripts/smoke_install.py` outside the checkout, including analysis,
  rhythm pagination, crops, charts, export and the missing-MCP error path.
- The targeted CLI help/version/configuration test passed (1 test); lock and diff
  checks passed. The unchanged engine's full-suite results are recorded below.
- No Python processes remained after verification.

## 0.5.1 engine release

Windows, CPython 3.12, November 6, 2026 (America/Los_Angeles). Verification was
planned before implementation in [CLI_PLAN.md](CLI_PLAN.md) and
[BEAT_EVAL_PLAN.md](BEAT_EVAL_PLAN.md). Muvi remains a CLI package with optional
MCP stdio integration; there is no browser application or HTTP service.

## Product and regression checks

`uv run --group dev --extra mcp pytest -q`: **73 passed in 148.80 seconds**.
The full suite exercises public commands through real subprocesses, the analysis
engine and actual MCP SDK; no tests were skipped.

- Analysis and cached reads; human/JSON output; Unicode filenames; full IDs, CLI
  prefixes/paths/`latest`; clean stdout, stderr progress and machine-readable errors.
- Sections, acoustic objects, paged occurrences, evidence, comparisons, hypothesis
  abstention, original audio crops, PNG/legend pairs and canonical export.
- Band attack timing, exact-window pulse estimates, missing events, quantization,
  timing changes, long gaps, pagination and explicit old-schema unavailability.
- Invalid files, arguments, spans and IDs; protected source/cache paths and explicit
  replacement of existing exports. Crop samples match the original source.
- Source identity, source-rate metrics, anti-phase audio, silence/noise, timestamp
  preservation, deterministic fixtures and atomic concurrent extraction.
- Help/version/configuration work without site-packages. Cached metadata and rhythm
  reads do not import numerical or plotting libraries.
- Real MCP initialization, discovery of 14 tools, analysis, rhythm and evidence
  retrieval, rejection of fabricated evidence, version-pinned WAV/PNG resources and
  normal client/server shutdown. Tests have bounded subprocess/request timeouts.
- A real Windows directory handle without delete sharing reproduced publication
  contention and verified recovery. Retries are limited to native errors 5/32/33,
  five attempts and 0.75 seconds total backoff. Permanent and unrelated failures
  propagate; publication remains atomic.
- The evaluation scorer gives no credit to missing answer fields, including empty
  expected event/gap lists.

Earlier native-module loading hangs in MCP were traced to importing NumPy after
reader threads started. MCP preloads DSP modules; ordinary cached CLI reads remain
lazy. Existing analyses remain readable and are not rewritten by retrieval.

## Independent agent evaluation

Terra used actual MCP; Luna used CLI and the new Muvi skill. Eight development and
eight held-out generated recordings had known attack timing. The tuned source and
skill were frozen before held-out evaluation. See [BEAT_EVALUATION.md](BEAT_EVALUATION.md)
for the protocol, per-component results, increased call counts, uncertainty and
preserved raw traces. This is not a real-music or raw-audio-model comparison.

The evaluated 0.5.0 implementation is commit `239ab99`. The 0.5.1 follow-up changes
Windows publication reliability and version labels. All eight held-out recordings
were reanalyzed with 0.5.1: rhythm, tempo, sound objects and evidence measurements
match the frozen evaluated output exactly. Perception module and skill hashes also
match. [Machine-readable equivalence](verification/beat-eval/final-equivalence.json)
records these checks. No perception tuning used held-out truth.

## Distribution and installation

- `uv build` produces the 0.5.1 wheel and source archive. Archive inspection found no
  HTTP service, static app assets or browser launcher; the source archive includes
  `skills/muvi/SKILL.md`. Wheel module bytes match the source checkout.
- `uv tool install` installed the wheel into an independent core-only environment.
  Both `muvi` and `music-genome` are standalone commands; `muvi --version` is 0.5.1.
- `scripts/smoke_install.py` passed outside the checkout. It verifies the installed
  package path, Unicode audio analysis, digest, schema discovery, paged rhythm,
  original WAV crop, PNG/legend export, canonical JSON and MCP configuration.
- The same smoke test confirms FastAPI, Uvicorn, Starlette and MCP are absent from
  the core environment and that requesting MCP gives a useful optional-install error.
- The Muvi skill passed the skill-creator validator and was used by Luna. It ships
  in the repository/source distribution; it is not automatically installed into a
  user's personal agent configuration.

`ruff check genome tests scripts`, `git diff --check` and `uv lock --check` passed.
Muvi starts no daemon. All spawned analysis, test and MCP processes terminated;
the final process inventory contained no remaining Python processes.

## Controlled benchmark

Full report: [verification/benchmark.json](verification/benchmark.json).

| Measurement | Observed result |
| --- | --- |
| Seeded controlled fixtures | 16 |
| Predeclared gates | All 5 passed |
| Clean pulse onset F1, 50 ms tolerance | 1.00 in all 8 cases |
| Largest clean-case median onset error | 2.97 ms |
| Largest clean-case octave-aware tempo error | 0.19% |
| Extraction + cache-write latency, 16-second fixtures | P50 1.100 s / P95 1.437 s |
| Sampled process peak RSS | 144 MiB |

The benchmark ran during concurrent verification on this machine. These are
warm-process observations, not a speed comparison or a latency/memory guarantee
for long recordings. The original benchmark's octave-aware global tempo metric
differs from the stricter local pulse-rate questions in the agent evaluation.

## Scientific limits

Synthetic truth applies only to generated signals. Real-track listener annotations,
raw-audio/image LLM comparisons, semantic model hints, calibration and targeted
separation were not performed. See [the ablation protocol](ABLATIONS.md).

Band changes are acoustic events, not automatically beats. Qualified periodicity is
not proof of perceived musical tempo, meter, downbeat or an independent bass source.
The global tempo/grid algorithm remains heuristic. Sample peak/RMS are not LUFS or
true peak; structural bands stop at 11,025 Hz. No isolated stems, MIDI transcription,
automatic mastering, third-party recordings or weights are shipped.
