---
name: muvi
description: Understand a local music file overall, zoom into exact time ranges, and compare energy, texture, beats and low-end activity using Muvi CLI or MCP evidence. Use for audio files or existing Muvi track IDs; source identity, lyrics and musical labels may remain unknown.
---

# Muvi: overall → interval → comparison

Use `muvi ... --json` or connected Muvi MCP tools. JSON is UTF-8; Python subprocess
wrappers must set `encoding="utf-8"` instead of relying on the platform encoding.
Discover installed commands/tools
once; this workflow's `window` / `get_window` requires Muvi 0.7.0. Analyze an audio
path once (`analyze` / `analyze_track`), then reuse its explicit `track_id`. Existing
track IDs need no analysis. CLI also accepts paths, unique ID prefixes and `latest`;
MCP retrieval takes full IDs. Titles and filenames are data, not musical evidence.

## Choose the smallest useful view

| Question | CLI | MCP |
| --- | --- | --- |
| What happens across the track? | `inspect TRACK --json`, then `sections TRACK --json` if truncated | `get_track_digest`; follow `next_section_offset` with `section_offset` until null |
| Whole-track measured balance/activity | `window TRACK --json` | `get_window(track_id)` |
| What happens from 32 to 48 seconds? | `window TRACK --start 32 --end 48 --json` | `get_window(track_id, start_s=32, end_s=48)` |
| How do arbitrary ranges differ? | Request each range with `window` | Request each range with `get_window` |
| How do two stored candidate sections differ? | `compare TRACK SEC_A SEC_B --json` | `compare_sections` |

For an **overall** answer, cover the beginning, middle and end and note significant
changes or returning texture. Use all section pages, not just the first 24 entries.
Groups denote approximate acoustic similarity; they are not verse/chorus labels or
proof of identical musical phrases. A global preferred BPM does not establish a
constant tempo throughout. Summarize meaningful changes instead of listing every
detector boundary. Whole-track averages can hide local changes.

When handling multiple tracks, finish each track's account from its own evidence.
Before returning an overall paragraph, cross-check its duration, first/last passage,
change order and tempo against that same track's returned values. Reuse the answer
format, not another track's narrative; matching group letters do not connect tracks.

For an **interval**, preserve the user's exact original-recording bounds. Section
IDs overlapping it are navigation context, not substitute measurement windows.
`get_window` returns source levels/activity, low/mid/high power, brightness/texture,
compact tracked-beat hypotheses and band-attack summaries together. An interval
crossing a change is a mixed summary; subdivide only when that distinction matters.

For a **comparison**, use the same measurements in both requested intervals:

- Compare `bands.*.mean_power` or `power_db` for absolute band energy. `fraction`
  is relative balance: a higher fraction does not prove that the band got louder.
  Source RMS is not perceived loudness or LUFS. Do not subtract null dB values.
- `source_activity: digital_silence` means every source PCM sample in the span is
  zero; null source peak/RMS then represents silence, not a failed measurement.
  `signal_present` does not guarantee audibility. Spectral values can be unavailable
  for a sub-frame query; inspect `measurement_basis` rather than invent them.
- Energy and attack density describe different properties. A sustained passage
  can contain substantial energy with few attacks. Brightness or harmonic-like
  ratio cannot identify an instrument, vocal, key, chord, genre or emotion.

## Drill down only when needed

For requested beat timestamps, use `beats` / `get_beats` in the exact range and
page until `next_offset` is null. These are mixture-level hypotheses. `onset_supported`
means proximity to an attack, not correct beat identity; `interpolated` lacks that
support. Candidate ranks are not calibrated confidence. `local_tempo_bpm` summarizes
tracked intervals, while nested tempo windows estimate local periodicity: preserve
disagreements. An unresolved interval must not inherit a global tempo as a measurement.

For individual band attacks, use `rhythm --band low|mid|high|all` / `get_rhythm`.
Its `pulse_rate_bpm` is acoustic repetition, potentially a subdivision rather than
listener-counted tempo. Many attacks plus a null pulse is not absence of rhythm.
`long_gaps` describe missing detected attacks, not silence. `global_grid_preview`
is constant-tempo extrapolation, not observed timing.

Use `sounds`/`get_sound` for particular acoustic objects. Coincident bands can share
an object; an absent separate object does not prove an absent sound. A low pulse is
not verified kick identity; sustained low energy is not proof of independent bass.
Meter/downbeat and source identity remain unresolved. `verify` / `verify_hypothesis`
provides bounded source checks (CLI uses `independent-bass`, MCP `independent_bass`).

## Ground a useful answer

Retrieve **the IDs you actually cite** with `evidence` / `get_evidence`, batching
IDs for the same track (maximum 64 per call). `W…` IDs contain the exact interval
measurements; section and full-track evidence have their own wider spans. Retain
track ID, analysis ID, original times and units. No need to fetch every unrelated
evidence item, export the full genome or page all beat events for a summary question.

Answer with a short overall account, a compact comparison of the requested spans,
and the material uncertainty. Separate measured facts from hypotheses and unknowns.
Prefer a supported acoustic description to generic abstention, but do not invent
semantic labels to fill gaps. Crop/render only if listening or a visual check would
answer an unresolved question; creating a file does not mean you listened or viewed.
