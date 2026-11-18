# Paired-image evaluation

## Protocol fixed before implementation

Freeze each reader page at 1000 × 1440 pixels. Stack the anonymized 0.8.5 tiles on the baseline page and the three revised panels on the new page. Keep original time ticks and axis labels. Randomize A/B per pair and reuse that mapping across versions. Each run gets a fresh context, one anonymous PNG, and the [same prompt](verification/pair/reader-prompt.txt). Keep the mapping, parameters, audio, and scores outside the reader context.

- Real drops. Use the supplied baseline and its −5.6 dB gain on the reference. Check two independent, correctly directed properties with a visible location. Have a listener check the interpretation against the clips.
- Controlled sounds. Program the same pulse, pitches, attack times, and per-band component energies. Change only low decay and mid duration, with compensating component gains. Score each direction separately. A count alone earns no credit.
- Gain. Render the same mixture and a scaled copy after compensating the gain. Require matching shapes and phrasing without invented rhythm or instrument changes.

Score each property as supported, missed, incorrect, or unresolved. Record the reader's actual answer even when a control fails. Verify the packaged CLI, MCP PNG retrieval, stale analyses, unresolvable hits, and release artifacts. No source recordings enter the public distribution.

## Results on November 18, 2026

Nine fresh GPT-6.1 Terra contexts each received one PNG named `page.png` and the exact neutral prompt. The transcripts contain zero tool calls. The baseline uses the supplied drop comparison split into its two original tiles, with the titles masked. Both generated controls use the 0.8.5 single-track chart design. Display gains were masked in the paired reader pages. Original timestamps and musical markings remained visible. The evaluator saved the random mapping before reading and kept it fixed across all rounds. [Answers, PNG hashes, mapping, parameters and measurements](verification/pair/readings.json)

| Property | 0.8.5 baseline | First paired view | Released view |
| --- | --- | --- | --- |
| Real drop, B fills more midrange gaps | Supported | Incorrect direction | Supported in P and F |
| Real drop, first selected A low ridge descends for longer | Unresolved | Supported | Supported at 182.044 s vs 168.008 s in H |
| Real drop, B has more intervening detected activity | Supported | Seen, but inferred slower musical pulse | Local spacing cited. Exact subdivision unresolved |
| Controlled B has longer low decay | Supported | Supported | Supported, localized to the first 200–450 ms |
| Controlled B sustains the mid sound through the gap | Supported | Supported | Supported at 1.6–2.2 s |
| Gain copy has matching phrasing and shape | Supported | Supported | Supported, reader prescribed no edit |

The original chart and neutral prompt already recovered the broad real-drop difference and both fixture directions. The new information was the location and direction of a low-frequency sweep. At 60, 100 and 200 ms after A's first selected attack, the strongest 25–225 Hz bins were 129, 86 and 54 Hz. B reached 54 Hz by 60 ms. A separate sustained band becomes strongest in B later in the window. This supports a listening experiment on the first hit. Three RMS traces cannot establish a typical pitch trajectory or identify a kick or bass stem.

The first paired reader treated the 79.5 BPM tracker hypothesis as a slower performance and reversed the midrange phrasing. The released page adds a common 250–2000 Hz power curve and shows the supplied 160 BPM project tempo alongside the tracker rate. The reader then called B's mid-band power more even. The 10th–90th percentile spread was 11.28 dB in A and 4.87 dB in B, with B's 10th percentile 8.14 dB higher. Its broader claim that B also sustains *more low energy* remains unresolved. Both have overlap. Rechecking the same pair after this correction measures the change on this case only.

The original near-match in breakdown low power reproduced at −31.45 and −31.35 dB. The drop's broadband detector rates reproduced at 5.04 and 9.38 attacks/s. Neither value was shown to the reader. The controlled fixture had identical 120 BPM timing and pitch sequences, with low decay constants of 34 and 140 ms and mid gates of 85 and 340 ms. Measured low/mid mean powers differed by less than 0.05 dB. Residual high-band energy was below −75 dB in both. The reader's suggestion of extra controlled subdivisions is unverified; the programmed onset positions are identical. The gain control uses a −9 dB copy with exactly compensating display gain.

The original listener judgment that the recordings sound different motivated this test. A new listener check of the specific musical interpretation is pending. The local evaluation bundle contains every PNG at the size sent, every answer, the exact prompt, the final legends and the fixture parameters.

The phrase uses the existing analysis sample rate and a log-frequency display of Hann-windowed spectra. A separate short RMS window preserves time detail for low attacks. The 2048-sample spectrum resolves roughly 10.8 Hz per bin and integrates about 93 ms of signal. Neighboring ridges, attacks and decays can overlap at that resolution. [FMP log-frequency methods](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C3/C3S1_SpecLogFreq-Chromagram.html), [librosa onset tutorial](https://librosa.org/doc/main/auto_tutorials/01-intro/05-onsets.html)
