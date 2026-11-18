# Paired-image evaluation

## Protocol fixed before implementation

Freeze each reader page at 1000 × 1440 pixels. Stack the anonymized 0.8.5 tiles on the baseline page and the three revised panels on the new page. Keep original time ticks and axis labels. Randomize A/B per pair and reuse that mapping across versions. Each run gets a fresh context, one anonymous PNG, and the [same prompt](verification/pair/reader-prompt.txt). Keep the mapping, parameters, audio, and scores outside the reader context.

- Real drops. Use the supplied baseline and its −5.6 dB gain on the reference. Check two independent, correctly directed properties with a visible location. Have a listener check the interpretation against the clips.
- Controlled sounds. Program the same pulse, pitches, attack times, and per-band component energies. Change only low decay and mid duration, with compensating component gains. Score each direction separately. A count alone earns no credit.
- Gain. Render the same mixture and a scaled copy after compensating the gain. Require matching shapes and phrasing without invented rhythm or instrument changes.

Score each property as supported, missed, incorrect, or unresolved. Record the reader's actual answer even when a control fails. Verify the packaged CLI, MCP PNG retrieval, stale analyses, unresolvable hits, and release artifacts. No source recordings enter the public distribution.
