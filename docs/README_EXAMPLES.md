# README examples

Both charts and the comparison use the same recording:

- **Track:** On & On (feat. Daniel Levi), by Cartoon, Jéja and Daniel Levi.
- **Source:** [official NCS page](https://ncs.io/onandon). Music provided by NoCopyrightSounds.
- **Input:** the official MP3 used in the existing real-music evaluation, duration 208.00106575963719 seconds.
- **SHA-256:** `8dadfc64562b8234f5bf3b3c2ea536cbe4bc088a8df9bd923b0219035fcf0eae`.
- **Analysis:** `dsp-0.6.0-6f2fa4bfb7ea`; chart renderer `tile-v2`, exported with Muvi 0.8.4.

The images are unaltered `muvi render` output, not interface mockups. Original
MP3 coordinates are used; they need not match the timing of a YouTube upload.
No recording is bundled in the repository or README assets.

After analyzing that recording:

```sh
muvi render latest --start 0 --end 208.00106575963719 -o whole.png
muvi render latest --start 64 --end 80 -o detail.png
muvi compare latest --a 32 48 --b 64 80 --json
```

## Comparison values

These are B minus A, with A = [32,48) seconds and B = [64,80) seconds.
The values below and in the README are rounded to two decimal places.

| Band | Power change (dB) | Attack rate A (/s) | Attack rate B (/s) | Rate change (/s) |
| --- | ---: | ---: | ---: | ---: |
| Low | +5.50 | 7.81 | 6.13 | -1.69 |
| Middle | +0.25 | 5.69 | 6.75 | +1.06 |
| High | +0.03 | 3.19 | 5.31 | +2.13 |

Window evidence IDs: `Wc17dd24fc41da8677eb5`, `Wff965a7a75367f484a82`.
Energy and attack rate are different measurements. Neither identifies an
instrument, establishes perceived loudness, or certifies beat correctness.

## Media storage

The two PNGs are hosted as attachments to the existing
[0.8.3 release](https://github.com/flrngel/muvi/releases/tag/v0.8.3), separately
from its package downloads. They were exported later using 0.8.4; no package
release was created for this documentation change. Git contains only the links.
