# Real-music beat evaluation — Muvi 0.6.0

2026-11-08. **Mean strict beat F1 improves from 55.1% to 67.4% on six fixed
held-out excerpts; two cases regress.** This release provides actual tracked
timestamp hypotheses and clearer uncertainty. It does not establish reliable beat
tracking for arbitrary music, meter recognition or independent bass identification.

## What changed and why

The [research and causal diagnosis](REAL_BEAT_RESEARCH.md) identify two distinct
limitations: testing almost all attack intervals against one pulse fails on mixed
subdivisions, and the old global tempo grid never followed actual beat positions.
The acoustic `rhythm` output retains its meaning. New `beats` / `get_beats` uses
balanced band/mixture novelty, Fourier-supported periodicity and local-tempo dynamic
programming, with explicitly supported and interpolated points. The package and
pipeline are 0.6.0; schema 0.3.0 retains old analysis readability. No dependency or
pretrained weight was added.

## Original three recordings: development, not accuracy ground truth

Official NCS downloads and hashes from the earlier real-music examples are retained.
Queries use the same original-coordinate windows; no favorable excerpt replacement.

| Recording | Old preferred BPM | New preferred hypothesis | Octave alternative |
| --- | ---: | ---: | ---: |
| [Cartoon/Jéja — On & On](https://ncs.io/onandon) | 69.65 | 173.998 | 87.019 |
| [DEAF KEV — Invincible](https://ncs.io/invincible) | 199.79 | 99.991 | 199.981 |
| [Elektronomia — Sky High](https://ncs.io/skyhigh) | 63.95 | 127.985 | 63.953 |

All nine beat queries at [32,48), [64,80), [96,112) now return tracked hypotheses
and a local tempo summary. **Availability is not accuracy.** The original low/high
acoustic queries still have 23/24 unresolved rates, correctly retaining their
different semantics. These recordings have no manual beat reference in this work.

Sky High [96,112) illustrates the distinction: all-band attack repetition is
512.032/min while the tracked interval summary is 129.199 BPM. In [64,80), the
tracker explicitly marks 77.171516–78.866577 as unsupported inside a larger
detected-attack gap. On & On [32,48) still has changing initial tracked intervals
despite 44/44 onset-supported points; that support cannot prove correct beat phase.

Example, using the user's existing local file:

```sh
muvi analyze on-and-on.mp3 --json
muvi beats latest --start 32 --end 48 --limit 128 --json
muvi rhythm latest --band low --start 32 --end 48 --json
# Retrieve the evidence_ids returned by these calls:
muvi evidence latest E0043 --json
```

Evidence IDs are analysis-local; use the returned ID, not this example blindly.

## Held-out real audio with reference beats

The [plan](REAL_BEAT_PLAN.md) fixed RWC P001/P011/P021/J001/J011/J021, source
excerpts [30,75), and scoring before implementation. Code and skill were frozen at
2026-11-09 03:13:24 UTC (November 8 local), before reading any numeric reference.
All six were evaluated; no post-result parameter changes, phase shifts, metrical
rescaling, replacements or exclusions were made.

Reference beats come from the curated [RWC 2.0 annotations](https://github.com/rwc-music/rwc-annotations)
at revision `0a1a6c31dbe73a7f5d44f7caef8cd0999402a4c2`, matched to
[RWC 2.0 audio](https://zenodo.org/records/17177919). Scoring uses excerpt [5,45),
equivalent to original [35,75), one-to-one matching within **70 ms**, without
half/double credit. The baseline is the old inferred constant grid; the new output
is the full tracked sequence, including interpolated hypotheses. This comparison
measures offered timestamp hypotheses, not equally implemented trackers.

| Reference recording | Baseline F1 | New F1 | New precision | New recall | Matched median error |
| --- | ---: | ---: | ---: | ---: | ---: |
| RWC P001 | 66.7% | **57.0% ↓** | 57.3% | 56.7% | 17.6 ms |
| RWC P011 | 66.7% | **100.0%** | 100.0% | 100.0% | 14.5 ms |
| RWC P021 | 100.0% | **100.0%** | 100.0% | 100.0% | 10.6 ms |
| RWC J001 | 0.0% | **25.0%** | 35.7% | 19.2% | 5.5 ms |
| RWC J011 | 0.0% | **70.0%** | 74.6% | 65.9% | 17.1 ms |
| RWC J021 | 97.1% | **52.6% ↓** | 77.5% | 39.9% | 22.4 ms |
| **Unweighted mean** | **55.1%** | **67.4%** | | | |

Pop mean: 77.8% → 85.7%; jazz mean: 32.4% → 49.2%. Only six convenience samples
were used; these are not population estimates or statistical significance claims.
Matched timing error excludes missed/false beats and must be read with F1.

Remaining failures are material. J021 and J001 choose roughly half the supplied
metrical level. P001 gets the approximate tempo but misses the reference beat
phase frequently. J011's local rates change markedly. All 24 held-out query windows
return `inferred`, yet their accuracy varies widely: J021 has 100% onset support
at 52.6% F1, and J001 has 96.4% support at 25.0% F1. **An available inference or
high onset-support fraction is not a calibrated confidence or quality gate.**

## Independent consumers and audit

Fresh Terra (`gpt-6.1-terra`) and Luna (`gpt-6-luna`) consumed public tools and the
skill with isolated libraries. They could not inspect implementation, annotations,
song BPM metadata or each other's answers before submitting results. The six held-out
files had anonymous names. This is procedural blinding, not an OS-enforced sandbox.
The fixed questions requested all timestamps, local tempo, subdivisions, gaps,
meter/downbeat, independent bass and actually retrieved evidence.

Terra completed actual MCP stdio calls for all nine recordings and 33 windows,
including paging and evidence retrieval. It preserved one corrected enum error
(`independent-bass` CLI spelling vs `independent_bass` MCP enum). It identified the
support/accuracy distinction and the On & On timing issue without reference access.
Meter/downbeat remained unestimated; all nine independent-bass checks abstained.

After its blind submission, Terra independently scored raw references and exports
using maximum-cardinality dynamic programming. It reproduced all six F1/counts,
verified reference hashes, and confirmed that saved MCP beat objects exactly match
the scored exports. That later audit did not change its blind answers.

Luna completed the same nine recordings and 33 windows through actual CLI/skill
calls, including all beat and low-band attack pages and evidence retrieval. The
root's [consumer trace audit](verification/real-beats/consumers.json) confirms that
both agents returned every expected beat object with the exact analysis identity,
retrieved all cited beat/source-check evidence, and preserved 33 meter/downbeat
abstentions and nine independent-bass abstentions each. A deliberately malformed
track-ID CLI probe was retained separately as an expected error, not an analysis failure.

These tests establish evidence retrieval and interpretation, not human-like hearing
or superiority to an LLM given raw audio. No listening claims, model calibration,
separation or meter/downbeat benchmark are made.

## Reproduction and retained evidence

- [Scores and every case](verification/real-beats/scores.json),
  [source provenance](verification/real-beats/provenance.json),
  [source/skill freeze](verification/real-beats/freeze.json),
  [independent scoring audit](verification/real-beats/scoring-audit.json).
- Run `python scripts/score_real_beats.py MANIFEST BASELINE_EXPORT_DIR TUNED_EXPORT_DIR OUTPUT`.
  Export folders contain `CASE-export.json`; the manifest points at local reference
  CSVs. The scorer does no downloading or post-hoc correction. Its tests reject
  duplicate matching, half-beat phase shifts and subdivision credit.
- Full local audio, original failures, anonymous excerpts, raw calls/answers, exports
  and scripts remain under `artifacts/real-beat-tuning/`; they are ignored by Git.
  The official audio ZIP was read by HTTP ranges, not downloaded in full. ZIP CRC,
  source/excerpt SHA-256 and annotation SHA-256 were checked.
- RWC audio/annotations: CC BY-NC 4.0, local research inputs only, not package assets.
  Attribution: Goto et al. (2002/2003), Goto (2006), Balke et al. (2026),
  [RWC Revisited](https://transactions.ismir.net/articles/10.5334/tismir.326).
  NCS recordings also remain local and retain their original source metadata.

Regression, package-install and platform checks are listed in [VERIFICATION.md](VERIFICATION.md).
