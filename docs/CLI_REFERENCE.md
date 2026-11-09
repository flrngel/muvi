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
| `inspect TRACK [--flow-offset N]` | Compact digest with measured acoustic progression and qualified returns |
| `window TRACK [--start TIME --end TIME]` | Whole-track or exact-interval energy, activity, texture and compact rhythm |
| `sections TRACK [SECTION] --detail` | Candidate sections and bounded occurrences |
| `sounds TRACK --query bass --start 8 --end 16` | Search acoustic objects in an interval |
| `sound TRACK SOUND --offset 0 --limit 10` | One object's paged occurrences |
| `rhythm TRACK --band low --start 8 --end 16 --limit 128` | Paged attacks and local pulse evidence |
| `beats TRACK --start 8 --end 16 --limit 128` | Tracked beat hypotheses, local tempo and support |
| `evidence TRACK EVIDENCE [EVIDENCE ...]` | Measurements, units and provenance |
| `compare TRACK SECTION_A SECTION_B` | Compare candidate sections |
| `compare TRACK --a 13.25 29.75 --b 61.125 84.375` | Compare exact ranges, with computed energy and attack-rate changes |
| `verify TRACK independent-bass` | Bounded hypothesis check, including indeterminate results |
| `metrics TRACK --start 8 --end 16` | Source-rate sample peak, RMS and stereo metrics |
| `crop TRACK --start 8 --end 16 -o clip.wav` | Original-mixture audio crop |
| `render TRACK --start 8 --end 16 -o evidence.png` | Aligned chart plus JSON legend |
| `export TRACK -o genome.json` | Full canonical analysis |

Use IDs returned by your analysis. Follow `next_offset` until null when you need all
paged events. `crop`/`render` without `-o` return generated cache paths; `export`
without `-o` writes the full JSON to stdout.

Text output adapts to terminal width (`COLUMNS` when set; 100-column fallback).
Tables wrap cells, prose wraps, and Unicode wide/combining characters are accounted
for. Flow rows and the explicit ending carry their `FLOW_…` navigation IDs. Use
JSON for exact machine-readable strings; terminal width never changes JSON.

`render` writes a neighboring JSON legend. Its raw-array URI points to the library;
genome artifact paths remain relative to the analysis directory. Keep the library
for later retrieval. Existing exports require `--force`; original audio and managed
cache paths cannot be overwritten, including with that flag.

### Chart interpretation

The four aligned panels show spectral power, low/mid/high power, onset strength
and acoustic-object occurrences. The visible color scale uses window-normalized
digital power; the displayed power floor is −120 dB. Object labels name acoustic
descriptors, not separated instruments. All panels use original-track seconds.

Beat marks use the stored tracked sequence, never the legacy constant-tempo grid.
Solid green marks have detected-onset support; dashed amber marks are interpolated
and unsupported. Both are inferred timing hypotheses. Interpolation can continue
through silence; it is not evidence that a sound occurred. Missing/empty tracking
is labeled explicitly. For spans over 30 seconds or more than 64 beats, individual
marks are omitted with a count. Zoom to inspect them. Candidate boundaries appear
only in the object panel and are omitted when more than 24 would be drawn.

The JSON legend retains every in-range beat coordinate/support and candidate
boundary, display counts/limits, object names and provenance, even when marks are
omitted. The `tile-v2` cache identity preserves older images while generating the
corrected view from existing analyses; audio reanalysis is unnecessary.

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

Fifteen typed tools cover analysis, digests, exact windows, beats, rhythm, sections, sound search/detail,
comparison, evidence, crops, charts, hypothesis checks, source metrics and separator
availability. MCP additionally exposes `list_tracks` and version-pinned WAV/PNG
resources, for 16 tools total. Core installation needs none of the MCP SDK,
FastAPI, Uvicorn or Starlette; the optional SDK has its own dependencies.

Evidence carries `track_id`, `analysis_id`, original-coordinate `time_span`,
`evidence_ids` and `measurement_status`. `prompt` instructs consumers to use actually
received measurements/provenance, retrieve missing details, distinguish inference from observation, and abstain when
measurements cannot distinguish alternatives. The [skill](../skills/muvi/SKILL.md)
adds rhythm-specific usage and interpretation.

`get_track_digest(track_id, section_offset=0, flow_offset=0)` pages candidate sections in groups of
24; follow `next_section_offset` until null for complete coverage. CLI `sections`
already returns every candidate section. A first-page digest is not a complete timeline.

The `flow` view describes acoustic progression with band powers, relative energy,
detected-attack rates, computed changes and qualified `similar_to` relationships.
It aggregates neighboring candidate sections if all bands stay within 3 dB and
attack rates within max(0.5/s, 25%); comparison against the first member prevents
gradual drift from collapsing the whole track. These are disclosed heuristic
tolerances, not probabilities or perceptual-equivalence thresholds. Group letters
are not used to infer a return. Means are duration-weighted section means, not new
exact-window measurements; source silence and song-function labels are not inferred.

Flow pages contain at most 12 items. Follow `flow.next_offset` with `flow_offset`
(CLI `--flow-offset`) until null. `ending` exposes the final item even on a truncated
page; it does not replace omitted middle pages. `FLOW_…` is a view/navigation ID;
underlying `evidence_ids` resolve to section measurements. The method, parameters,
units and aggregates are provided inline. Raw sections remain independently pageable.

`get_window(track_id, start_s=0, end_s=None)` defaults to the whole track. Exact
requested intervals need not coincide with sections. Source RMS/activity uses
rounded source-sample bounds; spectral statistics select cached frame centers in
the half-open interval, with STFT context reported in `measurement_basis`. A query
shorter than one frame can have no spectral data while still containing source audio.
It returns compact beat/attack summaries; request paged `get_beats`/`get_rhythm`
only for individual events.

`compare_sections(track_id, range_a=[start,end], range_b=[start,end])` computes
exact-span changes using the same windows. Supply both ranges or both `section_a`
and `section_b`; incomplete or mixed inputs are rejected. Existing section-ID calls
retain their response contract. Range mode returns `window_a`, `window_b`, `changes`
and exact `W…` evidence inline. A deterministic `summary` exposes scoped band-power
and every band-attack-rate change without another query. All deltas are B minus A. Per-band attack densities
normalize unequal durations; detected attacks are not beat counts. Power fractions
are not used to infer absolute changes. `within_1_db` describes a numerical range,
not perceptual sameness. Zero-power dB differences are null with explicit `to_zero`,
`from_zero` or `both_zero` status; missing spectral data uses `unavailable`.
Source RMS null deltas remain unavailable; inspect source activity in each input.

Window summaries have immutable `W…` evidence IDs. `get_evidence` retrieves the exact
measurement values, times, units and method from a lazily generated query artifact.
The library must accompany IDs; these query IDs are not embedded into the original
canonical genome. IDs with no stored query artifact are rejected. Concurrent readers
publish each summary atomically. Repeated cached queries avoid numerical imports.

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
  windows/W*.json        derived exact-interval summary and retrievable evidence
```

Analysis publishes atomically under a process lock. Cache identity includes audio
hash, pipeline version and parameter hash. Package 0.8.2 reuses pipeline 0.6.0;
window comparisons and derived flow do not require reanalysis. Pipeline 0.6.0 introduced
tracked beat hypotheses (schema 0.3.0). Reanalyze original audio to populate these
fields; older analyses return `available: false` from `beats`. Older 0.3.x libraries remain
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
