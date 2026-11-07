# Muvi 0.3.1 verification

Verified on Windows with CPython 3.12, November 6, 2026 (America/Los_Angeles).
The release was built from an initially empty repository. No external model, music
catalog, API key, third-party recording or GPU was used.

## Automated result

`uv run pytest -q`: **30 passed**. Coverage includes:

- Clean pulse timing at 90/120/150/180 BPM; shift counterfactual; silence and three
  stationary-noise seeds; source-identity abstention; quiet entrances and bright attacks.
- Original bytes and decoded samples; source-rate gain/clipping/stereo measurements;
  anti-phase stereo; invalid/nonfinite/multichannel inputs; short files.
- Canonical schema round trips and reference integrity; cache reuse; atomic concurrent
  extraction; older analysis retention; byte-reproducible seeded fixtures.
- Bounded upload streams before multipart spooling; unknown Host/cross-origin refusal;
  no arbitrary-path HTTP analysis; artifact traversal rejection; ranged audio serving.
- Digests, section comparison, exact crops, aligned PNG/JSON tiles, and absence of
  fabricated evidence. The external-answer scorer rejects missing/invalid/out-of-span answers.
- Real MCP SDK client: initialize, discover, analyze, retrieve digest, reject unknown
  evidence, and read WAV/PNG resources through version-pinned URIs.

The test environment emits one upstream Starlette deprecation warning about its
httpx-backed TestClient. It does not affect these passing assertions.

`node --check genome/static/app.js`: passed. `git diff --check`: passed after whitespace
cleanup. `uv build`: wheel and source archive built. An isolated installed-wheel smoke
test outside the checkout verifies packaged UI assets, HTTP routes, real audio
extraction, digest, playback artifact, and the generated MCP configuration.

## Controlled benchmark

Full machine-readable result: [verification/benchmark.json](verification/benchmark.json).

| Measurement | Observed result |
| --- | --- |
| Seeded controlled fixtures | 16 |
| Predeclared gates | All passed |
| Clean pulse onset F1, 50 ms tolerance | 1.00 in all 8 cases |
| Largest clean-case median onset error | 2.97 ms |
| Largest clean-case octave-aware tempo error | 0.19% |
| Two controlled arrangement boundary F1 scores, 0.5 s tolerance | 1.00, 1.00 |
| Extraction + cache-write latency, 16-second fixtures | P50 0.365 s / P95 0.393 s |
| Sampled process peak RSS | 142 MiB |

These are warm-process observations on this machine. The memory sample includes the
Python process and imports; it is not a guarantee for ten-minute or high-rate inputs.
The boundary checks are regression fixtures used during development, not a held-out
real-music estimate. Synthetic truth applies only to the generated signals.

Observed failures led to concrete corrections: an integer-lag third-period tempo alias;
quiet entrances hidden by dominant low-band energy; sustained bass dominating transient
descriptors; random noise receiving a tempo/pattern; and timestamped float-WAV headers
defeating demo cache reuse. The final benchmark and regression tests exercise the fixes.

## Browser verification

The actual loopback workspace was exercised in the in-app browser at desktop size and
390×844. Checked first-run layout, generated example, local WAV upload, progress,
persistent library, cached reanalysis, playback, seek, waveform/spectrum/rhythm views,
section zoom/reset, bounded sound audition, section looping, evidence records, section
comparison, PNG + JSON tile, canonical JSON download, MCP configuration copy, invalid
audio recovery, and responsive evidence navigation. No JavaScript console errors were
observed during the final checked workflows. UI testing used the real analysis engine.

## Deliberate limits

The blueprint's comparative research claim is **not established**. Raw-audio/image
baselines, LLM answer comparisons, permissioned real-track listener annotations,
calibration, MOSS/CLAP-style semantic hints, and targeted separation were not run.
The external ablation protocol and grounding scorer are provided for that next stage.

Section groups, acoustic roles, event families and beat grids remain heuristic.
Unknown source identity is a supported result. No isolated instruments, precise MIDI,
BS.1770 loudness, true peak, or automatic mastering are claimed. Commercial model
rights are not implied: no optional weights are shipped.
