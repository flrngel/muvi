# Muvi 0.4.0 CLI verification

Windows, CPython 3.12, November 6, 2026 (America/Los_Angeles). The
[verification contract](CLI_PLAN.md) was written before the CLI conversion.
This release replaces the browser application and HTTP service entirely.

## Product and regression checks

`.venv/Scripts/python.exe -m pytest -q`: **56 passed in 163.37 seconds** with the
MCP extra installed. The suite exercises the public CLI through real subprocesses,
plus the existing engine and tool tests.

- Analyze and cached reanalysis; human and JSON digests; full IDs, short prefixes,
  local paths and `latest`; empty libraries; global/subcommand flags; environment defaults.
- Unicode/spaced filenames; clean UTF-8 stdout; progress on stderr; quiet mode;
  JSON object/file/stdin arguments and typed-schema discovery.
- All direct evidence workflows: sections, sounds, paged occurrences, measurements,
  comparisons, hypothesis abstention, original crops, PNG/legend pairs, canonical export.
- Invalid files, malformed JSON, invalid tool arguments, nonexistent IDs, invalid
  timestamps and spans, ambiguous prefixes, exit status 2 and machine-readable errors.
- Existing exports require explicit replacement. Original audio and managed cache
  files cannot be overwritten, including with `--force`. Crop samples match the source.
- Help/version/MCP configuration work with Python site-packages disabled. Cached
  metadata commands do not import NumPy, SciPy, SoundFile or Matplotlib.
- Source bytes, source-rate gain/stereo metrics, anti-phase audio, timestamp shifts,
  quiet entrances, stationary noise, silence, reference integrity, atomic concurrent
  extraction, deterministic fixtures and preservation of old analysis versions.
- Actual MCP SDK client: initialize, discover 13 tools, analyze a local file, retrieve
  its digest, reject fabricated evidence, and read version-pinned WAV and PNG resources.
  Requests have a timeout so regressions cannot leave a test waiting indefinitely.

A Windows native-library loading hang was reproduced during the first analysis inside
an active MCP stdio session. A faulthandler trace located it in NumPy extension loading.
MCP now loads the native DSP modules before starting its reader threads. The real
client test then passed, including binary resources and normal process shutdown.
Ordinary cached CLI reads retain their lazy import path.

The original local `dsp-0.3.1-9ac2e98f5cb4` demo was also read successfully through the
new CLI. Its stored analysis was not rewritten. New analyses omit browser playback
copies and browser waveform arrays.

## Distribution and installation

- `uv build` produces the 0.4.0 wheel and source archive.
- Both archives were inspected: no HTTP server, static app assets or browser launcher.
- Core wheel requirements are NumPy, SciPy, SoundFile, Pydantic, Matplotlib and FileLock.
  The MCP SDK is an optional extra; no direct web dependencies remain.
- The wheel was installed with `uv tool install` into its own environment outside the
  repository. `scripts/smoke_install.py` runs outside the checkout and verifies the
  installed package path, Unicode audio analysis, digest, schema discovery, original
  WAV crop, PNG/legend export, canonical JSON and generated MCP configuration.
- The same smoke test asserts FastAPI, Uvicorn, Starlette and MCP are absent in the
  core environment and that requesting MCP gives a useful optional-install error.
- `muvi` and `music-genome` are installed as standalone commands. No daemon is started.

`ruff check genome tests scripts`, `git diff --check` and `uv lock --check` passed.
All spawned analysis, test and MCP processes terminated; no Python background
process remained after the final suite.

## Controlled benchmark

Full report: [verification/benchmark.json](verification/benchmark.json).

| Measurement | Observed result |
| --- | --- |
| Seeded controlled fixtures | 16 |
| Predeclared gates | All passed |
| Clean pulse onset F1, 50 ms tolerance | 1.00 in all 8 cases |
| Largest clean-case median onset error | 2.97 ms |
| Largest clean-case octave-aware tempo error | 0.19% |
| Extraction + cache-write latency, 16-second fixtures | P50 1.177 s / P95 1.744 s |
| Sampled process peak RSS | 145 MiB |

The benchmark ran during concurrent verification on this machine. These are
warm-process observations, not a latency or memory guarantee for long recordings.
Three fresh-process measurements gave median CLI help startup of 0.417 s and cached
digest startup of 1.974 s. Import-time inspection before the lazy-loading change
showed 6.237 s spent importing the engine alone. These figures are local observations;
the regression assertion is that cached reads load no numerical libraries.

## Deliberate scientific limits

Synthetic truth applies only to generated signals. Real-track listener annotations,
raw-audio/image LLM comparisons, semantic model hints, calibration and targeted
separation were not performed. No general-music QA accuracy claim follows from
these tests. See [the ablation protocol](ABLATIONS.md).

Roles, acoustic families, beat grids and candidate sections remain heuristic.
Instrument identity and independent bass can legitimately be indeterminate. Sample
peak/RMS are not LUFS/true peak; structural bands stop at 11,025 Hz. No isolated stems,
MIDI transcription, automatic mastering, third-party recordings or weights are shipped.
