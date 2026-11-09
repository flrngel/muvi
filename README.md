# Muvi

**See what's happening in your music.**

Muvi turns a song into charts you can look closely at. See where the sound changes,
zoom into the rhythm, and compare one passage with another. Your AI can use the
same charts and measurements to talk about the music with you.

Runs in your terminal, with audio files on your computer.

![Muvi's actual output for On & On: a whole song shown as sound energy, low/mid/high curves, sharp attacks and groups of similar sounds.](https://github.com/flrngel/muvi/releases/download/v0.8.3/readme-on-and-on-overview.png)

*An actual Muvi chart of **On & On** by Cartoon, Jéja and Daniel Levi.
Music provided by [NoCopyrightSounds](https://ncs.io/onandon).*

[Try it](#try-it) · [Use with your AI](#use-with-your-ai) · [All commands](docs/CLI_REFERENCE.md)

## Start with the whole song

Read the picture from left to right. Everything lines up with the same clock.

- **At the top:** low sounds sit near the bottom, high sounds near the top. Brighter areas have more energy.
- **In the middle:** three lines follow the low, middle and high frequencies. The spikes below them show sudden attacks in the sound.
- **At the bottom:** colored blocks show when groups of similar sounds appear.

You can see broad changes before choosing a moment to look at more closely.

```sh
muvi analyze "song.mp3"
muvi render latest -o song.png
```

For a written walkthrough from beginning to end, run `muvi inspect latest`.

## Look closer at the rhythm

Here is **1:04–1:20 of the same recording**. The pulses that were packed together
in the full song now spread out across the page.

![The same On & On recording enlarged to 64–80 seconds, showing individual attacks and green or amber beat marks.](https://github.com/flrngel/muvi/releases/download/v0.8.3/readme-on-and-on-detail.png)

The small green marks are estimated beats that line up with a detected attack.
Amber dashes fill gaps in the estimated timing. They make it possible to see
where the tracker has support and where it is guessing. Beat estimates can be wrong.

```sh
muvi render latest --start 64 --end 80 -o close-up.png
muvi beats latest --start 64 --end 80
```

The times stay relative to the original song. Click either image to open it at full size.

## Compare two moments

Does the low end get stronger? Do the sharp sounds become more frequent?

```sh
muvi compare latest --a 32 48 --b 64 80
```

For the recording above, comparing **0:32–0:48 → 1:04–1:20** gives:

| Part of the sound | Change in energy | Change in attacks per second |
| --- | ---: | ---: |
| Low | +5.50 dB | −1.69 |
| Middle | +0.25 dB | +1.06 |
| High | +0.03 dB | +2.13 |

The second passage has more low-frequency energy, even though low-frequency
attacks are less frequent. The high frequencies have almost the same energy,
with more frequent attacks.

These numbers describe the whole mix. They don't identify which instrument
changed or how much louder it feels. [Values and example source](docs/README_EXAMPLES.md).

## Try it

Requires Python 3.12 or 3.13. Install Muvi directly from Git:

```sh
uv tool install --python 3.12 "git+https://github.com/flrngel/muvi.git@main"
```

No song handy? Generate a short example and draw it:

```sh
muvi demo
muvi render latest -o demo.png
```

Or use your own recording:

```sh
muvi analyze "/path/to/song.mp3"
muvi inspect latest
muvi render latest -o song.png
```

`latest` is your most recently analyzed track. Choose time ranges within its length.
Charts are saved as PNGs with a JSON file containing the matching times and values.

Mac, Windows and Linux. WAV, FLAC, OGG and supported MP3 files, up to 10 minutes
and 200 MiB. [Tested platforms](docs/PUBLICATION.md) · [Options and limits](docs/CLI_REFERENCE.md).

## Use with your AI

Give your agent access to `muvi` and the [Muvi skill](skills/muvi/SKILL.md), then ask:

> Walk me through this song. Where does the low end become stronger?
> Compare 0:32–0:48 with 1:04–1:20 and show me the moments you're talking about.

Your AI writes the explanation. Muvi provides the charts, numbers and short audio
clips it can check. Add `--json` to commands when your agent needs the results as data.

<details>
<summary><strong>Connect through MCP</strong></summary>

Install the adapter and generate its configuration:

```sh
uv tool install --python 3.12 --force --no-build-package cryptography "muvi-genome[mcp] @ git+https://github.com/flrngel/muvi.git@main"
muvi mcp-config
```

Paste the emitted `mcpServers` object into your client's configuration and reconnect.
Generate it on each computer, since the paths are specific to that machine.
The binary-package option also supports installation on Intel Macs.
[Tool reference](docs/CLI_REFERENCE.md#typed-tools-and-mcp).

</details>

## A few things to know

Muvi works with the recording as a whole. It doesn't separate the bass or drums,
name every instrument, or reliably label verses and choruses. Beat timing and
groups of similar sounds are estimates you can inspect, not musical ground truth.

Analysis runs locally without an account, API key or model download. Your library
is saved in `~/.muvi`, including a copy of the audio. Muvi doesn't upload it;
an AI client may send retrieved results to its model provider.

<details>
<summary><strong>Update or remove Muvi</strong></summary>

```sh
uv tool install --python 3.12 --force --refresh "git+https://github.com/flrngel/muvi.git@main"
```

For MCP, rerun its installation command with `--refresh`, then regenerate the configuration.
To remove Muvi, run `uv tool uninstall muvi-genome`. Your audio library remains.

</details>

[Command reference](docs/CLI_REFERENCE.md) · [Development](docs/DEVELOPMENT.md) ·
[Music evaluations](docs/REAL_BEAT_EVALUATION.md) · [Report a problem](https://github.com/flrngel/muvi/issues)
