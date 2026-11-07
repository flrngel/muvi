# Muvi · Music Genome CLI

Music, made legible. Analyze a track, find its beat and low-end activity, and trace
every claim back to timestamped evidence. Runs locally on CPU with no account,
API key, GPU or model download. **0.5.1 includes band-specific rhythm evidence and resilient Windows publication.**

## Start in the terminal

Python 3.12 or 3.13. From this checkout, using [uv](https://docs.astral.sh/uv/):

```powershell
uv sync --locked
uv run muvi demo
uv run muvi analyze "C:\Music\track.wav"
uv run muvi sounds latest --query bass
uv run muvi rhythm latest --band low --start 8 --end 16 --json
uv run muvi inspect latest --json
```

For a standalone command outside this directory:

```powershell
uv tool install .
muvi --help
```

Alternatively, `python -m pip install .` in your chosen Python environment. No
public package publication is required. `music-genome` is an alias for `muvi`.
`python -m genome.cli` also works. A bare `muvi` shows help.

Human-readable output is the default. `--json` returns a single UTF-8 JSON document
on stdout; progress goes to stderr. `--quiet` suppresses progress. `--format json`
and `--format text` are explicit alternatives. Help and version always print text;
`mcp` speaks its stdio protocol.

## Follow the evidence

```powershell
muvi list
muvi inspect latest
muvi sections latest
muvi sections latest SEC_01 --detail
muvi sounds latest --query beat --start 00:08 --end 00:16
muvi sound latest S01 --limit 10
muvi evidence latest E0001 E0002
muvi rhythm latest --band low --start 00:08 --end 00:16
muvi compare latest SEC_01 SEC_02
muvi verify latest independent-bass
muvi metrics latest --start 8 --end 16
muvi crop latest --start 8 --end 16 -o clip.wav
muvi render latest --start 8 --end 16 -o evidence.png
muvi export latest -o genome.json
```

Use IDs returned by your analysis; section and sound IDs vary by recording.
`inspect` summarizes tempo candidates, sections, acoustic objects and recurrence.
`overview` remains an alias. The complete genome includes the provisional beat
timestamps and all events; `export` without `-o` writes that JSON directly to stdout.

Every `TRACK` position accepts an audio path, a full SHA-256 ID, a unique prefix of
at least eight hex characters, or `latest`. Paths are analyzed or loaded from cache
automatically. Ambiguous prefixes fail explicitly. `latest` is the track with the
newest completed analysis in this library; reading a cached track does not reorder it.

Times accept seconds, `MM:SS` or `HH:MM:SS`, including fractional seconds. Coordinates
always refer to the original recording. Crops are limited to 60 seconds and preserve
decoded source samples, sample rate and channels without normalization.

`crop` and `render` without `-o` return generated cache-file paths. With `-o`, `render`
writes both the PNG and a neighboring JSON legend; its raw-array URI points back to
the local library. Exported genome artifact paths remain relative to the analysis
directory. Keep the library if you need to retrieve the referenced audio or arrays.
Existing exports require `--force`; source audio and managed cache files remain protected.

## Let an LLM use it

The reusable [Muvi skill](skills/muvi/SKILL.md) describes CLI/MCP routing and evidence
interpretation. It can be copied into your agent's skill directory; no agent settings
are changed automatically. For rhythm, use `rhythm` / `get_rhythm` with the requested
band and exact interval. It returns paged attack timestamps, interval consistency,
local pulse rates, long gaps and support labels on the global grid preview.

The band channels are low (20–250 Hz), mid (250–2,000 Hz), high (2,000–11,025 Hz)
and all analysis bands. These are overlapping acoustic measurements, not stems.
The rate describes detected acoustic repetition and can differ from perceived musical
tempo. No stable rate does not prove absence of rhythm. A global grid point marked
`extrapolated` is not an observed attack. Older analyses return `available: false`
for rhythm until the original audio is reanalyzed.

An agent with shell access can use the CLI directly:

```powershell
muvi analyze "track.wav" --json
muvi tools --json
muvi tools get_audio_crop --json
muvi tool get_track_digest --arguments-file request.json --json
muvi schema
muvi prompt
```

`request.json` contains `{"track_id":"latest"}`. `--arguments-file -` reads JSON from
stdin; `--arguments` accepts inline JSON. All tool inputs are validated against their
typed schema, including rejection of extra fields. Tool calls accept the same track
references as direct commands. For concurrent agents, keep the returned full track
ID instead of relying on shared `latest` state.

Thirteen typed tools cover analysis, digests, rhythm, sections, sound search/detail, comparison,
evidence, crops, charts, hypothesis checks, source metrics and separator availability.
Evidence responses carry `track_id`, `analysis_id`, original-coordinate `time_span`,
`evidence_ids` and `measurement_status`. `prompt` supplies grounding instructions:
retrieve evidence before citing it, distinguish inference from observation, and abstain
when the measurements cannot distinguish alternatives.

For an MCP client, install the optional adapter and generate configuration:

```powershell
uv sync --locked --extra mcp
uv run muvi mcp-config
```

For standalone installation use `uv tool install ".[mcp]" --force`, then
`muvi mcp-config`. Paste the emitted `mcpServers` object into your client's configuration.
It contains the actual Python executable and absolute library path. `muvi mcp` runs
the stdio server; it exits when the client closes the connection. No client settings
are changed automatically. MCP includes `list_tracks` and version-pinned WAV/PNG
resources in addition to the thirteen tools. MCP retrieval takes the full `track_id`
returned by `analyze_track` or `list_tracks`; path/prefix/`latest` resolution is a CLI
convenience. Core installation requires none of the
MCP SDK, FastAPI, Uvicorn or Starlette; the optional SDK has its own dependencies.

## Library and scripting contract

Choose a library with `--data-dir DIR` before or after the command, or set
`MUVI_DATA_DIR`. The default is `~/.muvi`. Audio stays there unless you export it
or your connected assistant sends evidence to its model provider.

```text
<library>/<audio-sha256>/<analysis-id>/
  genome.json           strict canonical schema
  manifest.json         original/parameter hashes and initial artifact checksums
  audio/original        byte-identical input file
  audio/source.wav      source-rate double-precision decoded PCM
  arrays/features.npz   full-resolution numeric measurements
  images/*.png, *.json  aligned charts and legends, generated on demand
  clips/*.wav           original-mixture crops, generated on demand
```

Extraction publishes an analysis atomically under a process lock. The cache key
contains the audio hash, pipeline version and parameter hash. Existing 0.3.x
libraries remain readable. Analyzing the same audio creates a 0.5.1 version while
preserving the old analysis. Object and evidence IDs are local to an analysis.

| Exit status | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Controlled benchmark failed its acceptance gates |
| 2 | Invalid input, unavailable optional command, or file operation failure |
| 130 | Interrupted with Ctrl+C |

With `--json`, handled errors produce `{"error":{"code":"invalid_request","message":"..."}}`
on stdout and a diagnostic on stderr. Scripts should check the exit status before using
the result. A benchmark gate failure returns its report with `passed: false`.

Supported inputs are those decoded by libsndfile, including WAV, FLAC, OGG and MP3.
Limits: 200 MiB input, 0.1 seconds–10 minutes, mono/stereo, 8–192 kHz, and 384 MiB
decoded PCM. Some long high-rate recordings require a shorter excerpt.

## Verification and scientific limits

```powershell
uv sync --locked --extra mcp
uv run --extra mcp pytest -q
uv run ruff check genome tests scripts
uv run muvi benchmark -o artifacts/benchmark.json --force --json
uv build
```

See the [verification contract written before conversion](docs/CLI_PLAN.md),
[release results](docs/VERIFICATION.md), [original research record](docs/PLAN.md),
and [external-model ablation protocol](docs/ABLATIONS.md).

The [independent Terra/Luna evaluation](docs/BEAT_EVALUATION.md) records blind MCP and
CLI/skill trials, raw tool traces, actual improvements, conservative abstentions and
increased tool-call counts. Its small generated corpus is not real-music validation.

The deterministic CPU pipeline uses multi-resolution FFTs, spectral flux, band
envelopes, chroma, texture masks, provisional periodicity, feature-change segmentation
and recurring acoustic descriptors. Acoustic objects can contain overlapping sources;
“bass” searches low-frequency candidates and does not prove a bass instrument exists.
Sections, roles and beat grids are hypotheses. Instrument identity, downbeats, MIDI,
separated stems, calibrated probabilities, LUFS and true peak are not established.
Sample peak and RMS are explicitly labeled, and structural bands stop at 11,025 Hz.

Accuracy is verified on controlled generated signals only. General music QA accuracy,
real-track listener validation and comparisons against audio/image LLM baselines remain
unvalidated. No third-party recordings or model weights are bundled; demo audio is
original seeded synthesis. The web app, HTTP API, browser launcher and new browser
playback artifacts have been removed.
