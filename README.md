# Muvi

**Give language models evidence about music.**

Muvi turns a local audio file into a compact overview, exact time-range measurements,
tracked beat hypotheses and retrievable evidence. Ask what changes across a song,
compare the low end in two passages, or inspect the measurements behind an answer.

Local CPU analysis. No account, API key or model download. CLI first, optional MCP.

[Install](#install) · [Try it](#try-it) · [Use with an agent](#use-with-an-agent) ·
[CLI reference](docs/CLI_REFERENCE.md) · [Releases](https://github.com/flrngel/muvi/releases)

## Install

Requires **Python 3.12 or 3.13**. Install Muvi from `main`:

```sh
uv tool install --python 3.12 "git+https://github.com/flrngel/muvi.git@main"
```

Then run:

```sh
muvi --version
muvi demo
```

Expect `muvi 0.8.4`, followed by an overview of a generated 25.6-second audio example.
The demo needs no music download. This package is **not on PyPI**.

macOS 13+ on Apple Silicon/Intel is the installation target. Runtime tests passed
on macOS 15 for both architectures, plus Windows and Linux. See
[platform verification](docs/PUBLICATION.md) for the exact matrix and limitations.
Installation needs internet access; ordinary analysis runs locally afterward.

## Try it

These commands work immediately after `muvi demo`:

```sh
muvi inspect latest
muvi window latest --start 8 --end 16
muvi compare latest --a 0 8 --b 8 16
muvi beats latest --start 8 --end 16
muvi render latest --start 8 --end 16 -o evidence.png
```

`render` writes an aligned chart and neighboring JSON legend. Green beat marks have
detected-onset support; amber marks are interpolated hypotheses. Neither guarantees
a correct musical beat. Overview charts disclose omitted markers and retain their
coordinates in the legend.

For your own audio:

```sh
muvi analyze "/path/to/song.mp3"
muvi inspect latest --json
muvi compare latest --a 32 48 --b 64 80 --json
```

Choose ranges within the recording. Quote paths with spaces. `latest` means the
newest completed analysis in the selected library; scripts and concurrent agents
should keep the full `track_id` returned by `analyze --json`.

| Question | Command |
| --- | --- |
| How does the whole song develop? | `muvi inspect latest --json` |
| What happens in this exact passage? | `muvi window latest --start 32 --end 48 --json` |
| Did the low end or attack rate change? | `muvi compare latest --a 32 48 --b 64 80 --json` |
| Where are the inferred beats? | `muvi beats latest --start 8 --end 16 --json` |
| What attacks occur in the low band? | `muvi rhythm latest --band low --start 8 --end 16 --json` |
| Which acoustic objects recur? | `muvi sounds latest --query bass` |
| What supports this observation? | `muvi evidence latest E0001` |
| Can I listen to the original passage? | `muvi crop latest --start 8 --end 16 -o clip.wav` |
| Can I save the complete analysis? | `muvi export latest -o genome.json` |

Use evidence IDs from your own results. Whole-track flow can span several pages:
follow `flow.next_offset` with `muvi inspect TRACK --flow-offset N`. Time values
accept seconds or `MM:SS`. Run `muvi COMMAND --help` for options.

## Use with an agent

### CLI and skill

Give your agent shell access to `muvi` and the [Muvi skill](skills/muvi/SKILL.md).
The [release](https://github.com/flrngel/muvi/releases/tag/v0.8.3) includes a portable
skill ZIP: put its `muvi` folder in your agent's supported skill directory and
start a new session. Muvi does not edit agent settings automatically.

Try asking:

> Use Muvi to explain this track from beginning to end. Compare 32–48 seconds
> with 64–80 seconds in low/mid/high energy and attack behavior. Cite the original
> time ranges and distinguish measurements from guesses.

The workflow is **overview → exact window → comparison → evidence when needed**.
`--json` emits one UTF-8 document on stdout; progress goes to stderr. For wrappers,
decode stdout as UTF-8. Discover typed tools with `muvi tools --json` and read
the grounding instructions with `muvi prompt`.

### MCP

Install the optional adapter and generate configuration on the computer that will
run the server:

```sh
uv tool install --python 3.12 --force --no-build-package cryptography "muvi-genome[mcp] @ git+https://github.com/flrngel/muvi.git@main"
muvi mcp-config
```

The build restriction selects a compatible binary `cryptography` package, including
on Intel Macs. Paste the emitted `mcpServers` object into your MCP client's
configuration, then reconnect. **Generate it again on each computer**: Python and
library paths are machine-specific.

MCP exposes 16 tools plus WAV/PNG resources over stdio. Use full track IDs returned
by `analyze_track` or `list_tracks`; `latest` is a CLI convenience. The server exits
when its client disconnects. [Tool contracts and pagination](docs/CLI_REFERENCE.md).

## What Muvi knows

Muvi measures the original mixture. The source audio and versioned observations
are the reference; the language model interprets them. Comparisons calculate
changes deterministically and retain the exact original ranges and evidence.

- **Measured:** band energy, source RMS/activity, spectral texture and acoustic attacks.
- **Inferred:** beat timing, local tempo, candidate boundaries and descriptor similarity.
- **Unresolved:** instrument identity, independent bass/stems, meter and downbeats.

An attack is not automatically a beat. A larger low-band fraction does not prove
the bass got louder. Similar descriptors do not prove an identical phrase or chorus.
Interpolated beats can continue through silence. `digital_silence` means exactly
zero source samples; `signal_present` is not a claim of audibility.

Supported inputs: WAV, FLAC, OGG and MP3 when decodable by libsndfile. M4A/AAC is
not a promised format. Limits: 200 MiB, 0.1 seconds–10 minutes, mono/stereo,
8–192 kHz and 384 MiB decoded PCM. Structural analysis stops at 11,025 Hz.
This is not a stem separator, transcription system or mastering meter.

## Storage and privacy

The library defaults to `~/.muvi`. It contains a copy of the original audio,
measurements and generated crops/charts. Set `MUVI_DATA_DIR` or pass
`--data-dir DIR` to choose another location. Muvi itself does not upload audio;
a connected agent may send retrieved evidence to its model provider.

## Update or troubleshoot

To update to the latest `main`:

```sh
uv tool install --python 3.12 --force --refresh "git+https://github.com/flrngel/muvi.git@main"
```

For MCP, rerun its installation command above with `--refresh`, then regenerate
`muvi mcp-config`.

- **Python error:** keep `--python 3.12`; you do not need to replace system Python.
- **Range error:** use bounds within the duration shown by `muvi inspect`.
- **Output already exists:** choose another filename or use `--force` intentionally.
- **Unsupported audio:** convert it to WAV or FLAC first.
- **Remove:** `uv tool uninstall muvi-genome`. Your library remains in `~/.muvi`.

For a bug report, include `muvi --version`, OS/CPU architecture, the command and
error text. Share a small reproducible example when possible; do not post private audio.

## Verification and development

Verification runs locally when making changes. GitHub Actions is disabled.
[Publication results](docs/PUBLICATION.md) preserve the completed 0.8.3 platform
checks, including actual MCP calls and isolated installs on Windows, Linux and
both Mac architectures.

The 0.8.2 baseline passed **103 tests**, plus final chart checks, 16 real/control
charts and 20 terminal-width checks. Earlier independent Terra/Luna evaluations
retain both successful answers and mistakes. These are bounded tests, not a claim
of universal music understanding or human-level beat accuracy.

[Detailed verification](docs/VERIFICATION.md) ·
[Beat limitations](docs/REAL_BEAT_EVALUATION.md) ·
[Whole-track and comparison evaluation](docs/FLOW_COMPARISON_EVALUATION.md)

From a checkout:

```sh
uv venv --python 3.12
uv pip install --python .venv --only-binary cryptography --group dev ".[mcp]"
uv run --no-sync python -m pytest -q
uv run --no-sync ruff check genome tests scripts
```

This installation resolves platform-compatible wheels. `uv sync --locked` is also
available, but the existing development lock may require a cryptography source
build on Intel macOS. The package name is `muvi-genome`; `music-genome` is a CLI alias.
