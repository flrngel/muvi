# CLI and evidence reference

Start with [installation and first analysis](../README.md). `muvi --help` lists all
commands; `muvi COMMAND --help` describes their arguments.

## Track references, time and output

Every CLI `TRACK` accepts an audio path, full SHA-256 ID, unique hexadecimal prefix
of at least eight characters, or `latest`. Paths are analyzed or loaded from cache.
Ambiguous prefixes fail. `latest` is the newest completed analysis in the selected
library; reading a cached track does not reorder it. Use full IDs for concurrent agents.

Times accept seconds, `MM:SS` or `HH:MM:SS`, with fractional seconds. Coordinates
always refer to the original recording. Crops are at most 60 seconds and preserve
decoded source samples, rate and channels without normalization.

Human-readable output is the default. `--json` or `--format json` emits one UTF-8 JSON
document on stdout; progress goes to stderr. `--quiet` suppresses progress.
`--format text` selects human output. Help/version always print text; `mcp` uses stdio
protocol messages. `inspect` has an `overview` alias; a bare `muvi` prints help.

| Command | Purpose |
| --- | --- |
| `list` | List tracks, newest first |
| `inspect TRACK` | Compact tempo, rhythm, section and acoustic-object digest |
| `sections TRACK [SECTION] --detail` | Candidate sections and bounded occurrences |
| `sounds TRACK --query bass --start 8 --end 16` | Search acoustic objects in an interval |
| `sound TRACK SOUND --offset 0 --limit 10` | One object's paged occurrences |
| `rhythm TRACK --band low --start 8 --end 16 --limit 128` | Paged attacks and local pulse evidence |
| `evidence TRACK EVIDENCE [EVIDENCE ...]` | Measurements, units and provenance |
| `compare TRACK SECTION_A SECTION_B` | Compare candidate sections |
| `verify TRACK independent-bass` | Bounded hypothesis check, including indeterminate results |
| `metrics TRACK --start 8 --end 16` | Source-rate sample peak, RMS and stereo metrics |
| `crop TRACK --start 8 --end 16 -o clip.wav` | Original-mixture audio crop |
| `render TRACK --start 8 --end 16 -o evidence.png` | Aligned chart plus JSON legend |
| `export TRACK -o genome.json` | Full canonical analysis |

Use IDs returned by your analysis. Follow `next_offset` until null when you need all
paged events. `crop`/`render` without `-o` return generated cache paths; `export`
without `-o` writes the full JSON to stdout.

`render` writes a neighboring JSON legend. Its raw-array URI points to the library;
genome artifact paths remain relative to the analysis directory. Keep the library
for later retrieval. Existing exports require `--force`; original audio and managed
cache paths cannot be overwritten, including with that flag.

## Typed tools and MCP

```sh
muvi tools --json
muvi tools get_audio_crop --json
muvi tool get_track_digest --arguments-file request.json --json
muvi schema
muvi prompt
```

`request.json` can contain `{"track_id":"latest"}`. `--arguments-file -` reads stdin;
`--arguments` takes inline JSON. Inputs are validated against typed schemas and
extra fields are rejected. CLI tool calls resolve the same track references as
direct commands. MCP retrieval requires full IDs returned by `analyze_track` or
`list_tracks`; `latest`, file paths and prefixes are CLI conveniences.

Thirteen typed tools cover analysis, digests, rhythm, sections, sound search/detail,
comparison, evidence, crops, charts, hypothesis checks, source metrics and separator
availability. MCP additionally exposes `list_tracks` and version-pinned WAV/PNG
resources, for 14 tools total. Core installation needs none of the MCP SDK,
FastAPI, Uvicorn or Starlette; the optional SDK has its own dependencies.

Evidence carries `track_id`, `analysis_id`, original-coordinate `time_span`,
`evidence_ids` and `measurement_status`. `prompt` instructs consumers to retrieve
evidence before citing it, distinguish inference from observation, and abstain when
measurements cannot distinguish alternatives. The [skill](../skills/muvi/SKILL.md)
adds rhythm-specific usage and interpretation.

## Library layout and versions

Use `--data-dir DIR` before or after the command, or set `MUVI_DATA_DIR`.
Default: `~/.muvi`.

```text
<library>/<audio-sha256>/<analysis-id>/
  genome.json           canonical schema
  manifest.json         original/parameter hashes and initial artifact checksums
  audio/original        byte-identical input
  audio/source.wav      source-rate double-precision decoded PCM
  arrays/features.npz   full-resolution measurements
  images/*.png, *.json  charts and legends, on demand
  clips/*.wav           original-mixture crops, on demand
```

Analysis publishes atomically under a process lock. Cache identity includes audio
hash, pipeline version and parameter hash. Package 0.5.2 retains pipeline 0.5.1:
documentation changes do not require audio reanalysis. Older 0.3.x libraries remain
readable; new analysis versions preserve previous ones. Object/evidence IDs are local
to an analysis, so retain `analysis_id` alongside citations.

## Exit codes and limits

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Controlled benchmark failed acceptance gates |
| 2 | Invalid input, unavailable optional command or file operation failure |
| 130 | Interrupted with Ctrl+C |

With `--json`, handled errors emit
`{"error":{"code":"invalid_request","message":"..."}}` on stdout and a diagnostic
on stderr. Check exit status before consuming output. A failed benchmark returns
its report with `passed: false`.

Input limits: 200 MiB, 0.1 seconds–10 minutes, mono/stereo, 8–192 kHz, 384 MiB
decoded PCM. Long high-rate recordings may require a shorter excerpt. Source
sample peak/RMS are not LUFS or true peak; structural analysis stops at 11,025 Hz.
No separated stems, MIDI, calibrated probabilities or automatic mastering are promised.
