# Muvi · Music Genome CLI

Turn local audio into timestamped evidence that people and language models can inspect.
Find acoustic attacks, compare sections, examine low-end activity, and check the
measurements behind an answer. Runs on CPU with no account, API key or model download.

**CLI only · Python 3.12–3.13 · Optional MCP · Version 0.8.1**

[Install](#install) · [First analysis](#first-analysis) · [Use-with-an-LLM](#use-with-an-llm) ·
[Command reference](docs/CLI_REFERENCE.md) · [Verification](#verification)

## Install

### macOS: Apple Silicon or Intel

The installation target is **macOS 13 or later**, using native Apple Silicon or Intel
Python. Dependency resolution was checked for both architectures with Python 3.12
and 3.13. **Execution on a physical Mac has not yet been tested.** Windows execution
and an independently installed wheel have been tested. See the
[platform check record](docs/verification/flow-comparison/release.json).

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
   If you already use Homebrew:

   ```sh
   brew install uv
   ```

   Without Homebrew, use uv's official installer:

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   Open a new terminal after installation.

2. Copy this source folder to your Mac, then run the following from that folder
   (the one containing `pyproject.toml`). Do not copy a Windows `.venv`.

   ```sh
   uv tool install --python 3.12 .
   uv tool update-shell
   ```

   uv obtains a compatible Python when needed and installs Muvi in an isolated tool
   environment. Open a new terminal if the shell path was updated.

3. Check the command and try the built-in audio example:

   ```sh
   muvi --version
   muvi demo
   muvi rhythm latest --band low --start 0 --end 8
   ```

**Already have the wheel?** Copy `dist/muvi_genome-0.8.1-py3-none-any.whl` to your
Mac's Downloads folder and replace step 2 with:

```sh
uv tool install --python 3.12 ~/Downloads/muvi_genome-0.8.1-py3-none-any.whl
uv tool update-shell
```

The same wheel works across operating systems; uv selects the platform's dependencies.
A source checkout or wheel is required: this project has not been published to PyPI.
Installation needs internet access for dependencies; ordinary analysis then runs locally.

### Windows and existing Python environments

With uv installed, the source-folder install is the same in PowerShell:

```powershell
uv tool install --python 3.12 .
uv tool update-shell
muvi demo
```

Alternatively, use `python -m pip install .` inside a Python 3.12/3.13 virtual environment.
`music-genome` is an alias; `python -m genome.cli` works in an environment containing Muvi.

## First analysis

```sh
muvi analyze ~/Music/track.wav
muvi inspect latest
muvi rhythm latest --band low --start 8 --end 16
muvi sounds latest --query bass
muvi sections latest
muvi inspect latest --json
```

On Windows, use a path such as `"C:\Music\track.wav"`. Quote paths containing spaces.
`latest` selects the newest completed analysis in your library. For scripts or multiple
agents, keep the full `track_id` returned by `analyze --json`.

| I want to… | Command |
| --- | --- |
| Understand the whole track | `muvi inspect latest --json` |
| Measure whole-track balance/activity | `muvi window latest --json` |
| Understand an exact interval | `muvi window latest --start 32 --end 48 --json` |
| Track musical beat hypotheses | `muvi beats latest --start 8 --end 16 --json` |
| Inspect local pulse timing | `muvi rhythm latest --band low --start 8 --end 16 --json` |
| Retrieve supporting measurements | `muvi evidence latest E0001 E0002` |
| Check whether bass is identifiable | `muvi verify latest independent-bass` |
| Compare exact intervals | `muvi compare latest --a 32 48 --b 64 80 --json` |
| Compare candidate sections | `muvi compare latest SEC_01 SEC_02` |
| Export an original-mixture clip | `muvi crop latest --start 8 --end 16 -o clip.wav` |
| Export a chart and its legend | `muvi render latest --start 8 --end 16 -o evidence.png` |
| Export the complete analysis | `muvi export latest -o genome.json` |

Use the evidence and section IDs returned by your own analysis. `muvi --help` and
`muvi COMMAND --help` list options; [the reference](docs/CLI_REFERENCE.md) explains
track references, timestamps, pagination, output contracts and library layout.

## Use with an LLM

### CLI or skill

Give an agent shell access to `muvi` and the [Muvi skill](skills/muvi/SKILL.md).
Copy that skill folder into the skill directory supported by your agent if needed;
Muvi does not modify agent settings automatically.
The standalone `dist/muvi-skill-0.8.1.zip` contains the same `muvi/SKILL.md` for
copying to another computer. For Codex on macOS, extract the `muvi` folder into
`~/.codex/skills/`, then start a new session and ask it to use `$muvi`.

```sh
muvi analyze track.wav --json
muvi tools --json
muvi window latest --start 32 --end 48 --json
muvi tools get_window --json
muvi prompt
```

`--json` writes one UTF-8 JSON document to stdout; progress stays on stderr.
The skill guides **overall → exact interval → comparison**. For arbitrary ranges,
use `compare TRACK --a START END --b START END` for computed energy and attack-rate
changes with exact evidence inline. Section-ID comparison remains available.
`inspect` adds measured acoustic progression; follow `flow.next_offset` using
`--flow-offset` to cover long tracks. The agent uses received evidence and preserves uncertainty about instruments,
meter and downbeats; it need not fetch every beat timestamp for a summary question.

### MCP

From the source folder, install the optional adapter and print client configuration:

```sh
uv tool install --python 3.12 --no-build-package cryptography ".[mcp]" --force
muvi mcp-config
```

For a downloaded wheel, replace `".[mcp]"` with
`"/path/to/muvi_genome-0.8.1-py3-none-any.whl[mcp]"`.
The build restriction lets Intel Macs select an available `cryptography` wheel;
see [the platform check record](docs/verification/macos-install.json).

Paste the emitted `mcpServers` object into your MCP client's configuration. It contains
this machine's Python executable and library path: **generate it again on the Mac**,
rather than copying Windows paths. Restart/reconnect your client after configuration.

The server exposes 16 tools, including `list_tracks`, plus WAV/PNG resources. It uses
stdio and exits when the client disconnects. MCP retrieval takes the **full track ID**
from `analyze_track` or `list_tracks`; CLI aliases such as `latest` are not MCP IDs.
[Tool and scripting details →](docs/CLI_REFERENCE.md)

## What the evidence means

- `window` combines activity, source RMS, band power, texture and compact rhythm for
  the requested interval. `W…` evidence IDs are retrievable at those exact bounds.
  Band fractions describe relative balance, not absolute energy. Spectral statistics
  select cached frame centers; window context can extend up to 0.186 s beyond them.
- `digital_silence` means all source PCM samples in the interval are zero; null
  source peak/RMS represents that silence. `signal_present` is not an audibility claim.
- `beats` follows mixture novelty with local tempo and timing constraints. It returns
  paged beat hypotheses, local tempo, alternatives and unsupported spans. A point
  marked `onset_supported` is near an attack, not a verified correct beat;
  `interpolated` lacks that support. Unsupported windows return unresolved tempo.
- `rhythm` reports band attacks, local acoustic repetition, timing changes and long
  gaps. Bands are low (20–250 Hz), mid (250–2,000 Hz), high (2,000–11,025 Hz), or all.
- An attack is not automatically a musical beat. A pulse rate can differ from the
  tempo a listener counts; grid points marked `extrapolated` are inferred positions.
- A low-frequency object does not prove an independent bass instrument. Meter,
  downbeats, instrument identity and separated stems are not established.
- Results have original-recording timestamps and retrievable evidence. Analyses before
  0.6.0 return `available: false` for `beats`; reanalyze the original audio to upgrade.

WAV, FLAC, OGG and MP3 are supported when decodable by libsndfile; M4A/AAC is not a
promised input format. Limits are 200 MiB, 0.1 seconds–10 minutes, mono/stereo,
8–192 kHz and 384 MiB decoded PCM. Standard macOS SoundFile wheels bundle libsndfile
([upstream installation notes](https://python-soundfile.readthedocs.io/en/latest/#installation)).

The default library is `~/.muvi`; change it with `--data-dir DIR` or `MUVI_DATA_DIR`.
It stores a copy of the original audio and derived evidence. Muvi itself does not
upload audio; a connected assistant may send retrieved evidence to its model provider.

## Update, remove or troubleshoot

- **Update from source:** obtain the updated folder, then rerun
  `uv tool install --python 3.12 . --force` there. Keep `".[mcp]"` and
  `--no-build-package cryptography` if you use MCP. Regenerate `muvi mcp-config`.
- **Command not found:** run `uv tool update-shell`, then open a new terminal.
- **Unsupported Python:** use `--python 3.12`; the system Python need not be changed.
- **MCP unavailable:** install the optional adapter using the command above.
- **Remove the command:** `uv tool uninstall muvi-genome`. This leaves `~/.muvi`
  and original source files intact.

## Verification

Version 0.8.1 passes **96 tests**, actual MCP calls and an isolated installed-wheel
smoke test. It extends existing comparison and digest tools with exact-range arithmetic
and measured acoustic progression. It adds no public tool, dependency or extraction
model. The pipeline remains 0.6.0; existing libraries need no reanalysis.
The [fixed evaluation criteria](docs/FLOW_COMPARISON_PLAN.md) separate numerical
correctness, useful explanations and sufficient received evidence.
[Independent results](docs/FLOW_COMPARISON_EVALUATION.md) retain mistakes and limitations.
Version 0.7.0 previously passed 90 tests; [that skill evaluation](docs/SKILL_SCOPE_EVALUATION.md)
records its consumer errors separately from successful retrieval.

Version 0.6.0 passed **84 tests** (83 regression/feature tests plus the strict reference
scorer test), **16 controlled benchmark cases**, and actual MCP calls on Windows.
See [verification results](docs/VERIFICATION.md) for packaging and platform checks.

The [real-music evaluation](docs/REAL_BEAT_EVALUATION.md) includes independent
Terra/Luna consumers and six preselected pop/jazz excerpts with reference beats.
Mean strict beat F1 improved **55.1% → 67.4%**, but two excerpts regressed; half-tempo
and beat-phase errors remain. High onset support is not an accuracy estimate.
The earlier [synthetic evaluation](docs/BEAT_EVALUATION.md) covers acoustic pulse
questions. Broad music accuracy, calibrated confidence, meter/downbeat and comparisons
with raw-audio models remain unvalidated.

For development from a checkout:

```sh
uv sync --locked --python 3.12
uv run muvi demo
uv run pytest -q
uv run ruff check genome tests scripts
uv run muvi benchmark -o artifacts/benchmark.json --force --json
uv build
```

For MCP tests on Windows/Apple Silicon, use `uv sync --locked --extra mcp` and
`uv run --extra mcp pytest -q`. The current MCP lock contains a `cryptography` version
without an Intel Mac wheel; Intel users should use the standalone MCP installation
above unless they intentionally maintain a source-build environment.

[CLI verification plan](docs/CLI_PLAN.md) · [Beat evaluation plan](docs/BEAT_EVAL_PLAN.md) ·
[Research](docs/BEAT_RESEARCH.md) · [Further evaluation protocol](docs/ABLATIONS.md)
