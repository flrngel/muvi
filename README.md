# Muvi · Music Genome

Understand the shape of a track. Follow the evidence all the way back to the sound.

Muvi is a local Python application with a listening workspace and an MCP tool server.
It extracts measurements, recurring acoustic objects, pattern candidates, and section
changes from audio. An acoustic object is a recurring sound family in a mixture,
not a guaranteed isolated instrument.

## Run

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then from this folder:

```powershell
uv sync --locked
uv run muvi serve --open
```

On Windows, you can also double-click `start-muvi.cmd`. Open
[the listening workspace](http://127.0.0.1:8765) and choose **Try an example** or import
your own recording. Stop the server with Ctrl+C when you finish.

The server binds only to `127.0.0.1`. No account, model download, GPU, API key or cloud
service is required. Audio stays in the local library. Import supports formats decoded
by the bundled libsndfile, including WAV, FLAC, OGG and MP3. Limits are 200 MiB per
file, 0.1 seconds–10 minutes, mono/stereo, 8–192 kHz, and 384 MiB decoded PCM. Very
high-rate long recordings may need a shorter excerpt.

## Explore

- Switch between spectrum, waveform and rhythm; click the timeline or use the seek slider.
- Select a candidate section to zoom. **Full track** restores the overview.
- Audition a sound family, inspect its original occurrences, or follow an evidence ID.
- Compare sections on a shared measurement scale. Roles and A/B structure groups are inferred.
- Export the canonical JSON or a synchronized 1600×900 image with its JSON legend.
- Use Space/K to play or pause outside form controls. Use the loop control to repeat
  the selected interval or audition. All essential actions have keyboard controls.

The browser plays a 16-bit, source-rate monitoring copy without gain normalization.
Floating-point values beyond full scale clip in this monitoring copy. The original
uploaded file remains byte-identical, decoded source PCM is stored as double-precision
WAV, and evidence crops retain those samples and source channels without normalization.

## Connect an LLM

Choose **Connect AI** for a ready-to-copy configuration using the running Python
environment and the same library directory. Any MCP client supporting stdio can use it.
An independently installed command can instead be configured as:

```json
{
  "mcpServers": {
    "muvi": {
      "command": "/absolute/path/to/python",
      "args": ["-m", "genome.cli", "mcp", "--data-dir", "/absolute/path/to/library"]
    }
  }
}
```

Replace paths with those on your computer. The UI provides the actual paths automatically.
No external assistant is configured silently. Retrieved evidence may be sent to your
assistant's model provider according to that client's settings.

Start with `list_tracks` and `get_track_digest`. Drill down with `get_section`,
`find_sound`, `get_sound`, `compare_sections`, `get_evidence`, `get_audio_crop`,
`render_tile`, `verify_hypothesis`, and `get_master_metrics`. MCP also exposes local
`analyze_track`. `run_targeted_separation` explicitly reports that no separator is
installed. Images and crops include version-pinned MCP resource URIs; capable clients
can read the binary resources without needing direct filesystem access.

Every evidence packet includes an `analysis_id`, original-coordinate `time_span`,
`evidence_ids`, and `measurement_status`. The system guidance in **Copy guidance**
teaches an assistant to distinguish measurements, hypotheses and unresolved sources.
The guided workspace questions use deterministic tool results, not an undisclosed LLM.

HTTP clients can discover schemas at `/api/tools`, inspect `/openapi.json`, and call
`POST /api/tools/<name>` with `{"arguments": {...}}`. Uploads use `/api/upload` with a
multipart `file`, then poll `/api/jobs/<job_id>`. HTTP clients cannot ask the server to
analyze arbitrary local paths. Cross-origin requests and unknown Host headers are rejected.
This is a single-user loopback application, not an authenticated shared hosting service.

## CLI

```powershell
uv run muvi analyze "C:\Music\track.wav"
uv run muvi list
uv run muvi overview "sha256:<returned-hash>" --format text
uv run muvi render "sha256:<returned-hash>" --start 8 --end 16
uv run muvi tool find_sound --arguments '{"track_id":"sha256:<returned-hash>","query":"bass"}'
uv run muvi benchmark --output artifacts/benchmark.json
```

`music-genome` is an alias for `muvi`. Add `--data-dir <directory>` to any subcommand,
or set `MUVI_DATA_DIR`. The default library is `~/.muvi`; tests use isolated stores.

## Evidence and storage

```text
<library>/<audio-sha256>/<analysis-id>/
  genome.json            strict canonical schema
  manifest.json          original hash, parameter hash, initial artifact checksums
  audio/original         byte-identical uploaded file
  audio/source.wav       source-rate double-precision decoded PCM
  audio/preview.wav      16-bit browser monitoring copy
  arrays/features.npz    full-resolution numeric measurements
  images/tile-*.png/json on-demand synchronized charts and companion legends
  clips/*.wav            on-demand original-mixture crops
```

Extraction writes to a staging directory, then atomically publishes a complete analysis.
A process lock prevents duplicate extraction of the same content. Cache keys include
the audio hash, pipeline version and parameter hash. Older analyses remain readable;
reimporting the same file creates a new version after a pipeline update. Acoustic object
IDs are track-local and analysis-local. There is no cross-track source identity claim.

The CPU pipeline uses bounded SciPy/NumPy FFT blocks at 512/2048/8192 samples, 256-sample
hops, 22,050 Hz structural audio, spectral flux, band envelopes, log-frequency STFT
views, STFT chroma, median harmonic/percussive-like texture masks, provisional tempo,
feature-change segmentation, and incremental-attack descriptor clustering. The
log-frequency view and STFT chroma are not a CQT or a transcription. Long windows
never set attack timestamps. Weak unmatched events remain unassigned after the object cap.

## Verification and limits

```powershell
uv run pytest -q
uv run muvi benchmark --output artifacts/benchmark.json
uv build
```

See [the pre-implementation verification contract](docs/PLAN.md),
[the release verification record](docs/VERIFICATION.md), and
[the external-model ablation protocol](docs/ABLATIONS.md).

Current accuracy claims are limited to generated fixtures. General-music source
identity, real-track listener validation, LLM-vs-audio/image comparisons, calibrated
probabilities, semantic audio models, source separation and BS.1770 LUFS/true-peak
metering are **not validated or shipped**. Sample peak and RMS are not substitutes for
LUFS or true peak. Analysis bands stop at 11,025 Hz; they are not full-band mastering
metrics. This is an evidence explorer, not a guaranteed instrument transcriber.

The architecture follows the perception/reasoning distinction investigated by
[Carone et al.](https://proceedings.mlr.press/v303/carone26a.html), with images kept as
an audit surface rather than source proof. See the plan for primary and community
sources, qualifications and implementation tradeoffs. No third-party recordings or
optional model weights are bundled. Demo audio is original seeded signal synthesis.

