# Implementation and verification contract

## Product

Deliver a runnable, local-first Music Genome v1: original audio → versioned measurements
→ acoustic objects/patterns/sections → compact evidence digests → human and LLM tools.
No account, cloud upload, GPU, or LLM API key is required. The workspace should make
importing, listening, locating changes, and inspecting evidence immediate.

## Work items and acceptance

1. **Evidence engine (0.1.0).** Strict schema; immutable checksum-addressed original;
   bounded CPU DSP; tempo ambiguity; section proposals; acoustic objects and motifs;
   atomic cache and measured source-rate metrics. Establish generated ground truth first.
2. **Tool interface (0.2.0).** Hierarchical digests, section/sound search, comparisons,
   exact evidence retrieval, original crops, synchronized PNG + JSON tiles, claim
   verification, CLI, REST and standard MCP stdio. Unsupported capabilities explicit.
3. **Listening workspace (0.3.0).** Accessible responsive interface; uploads, live analysis
   progress, generated example, library, seeking/playback, sections, sound audition,
   evidence inspector, comparison, JSON export and LLM connection instructions.
4. **Release verification (0.3.1).** Controlled benchmark, browser workflows, installed
   package smoke test, MCP protocol integration, malformed inputs, concurrency and cache.

Each implementation is committed with its package version. Never call heuristic ranks
confidence probabilities, infer sources from spectral regions, or fabricate LLM answers.

## Verification specified before implementation

- Generated fixtures: pulse trains at multiple BPMs, silence, noise, tones, stereo
  cancellation, clipped audio, delayed entrances, repeated/changed arrangements,
  missing pulses and alternate bass bars. Seeds and exact sample-index truth retained.
- Timing: one-to-one onset F1 at 50 ms on clean pulse fixtures; median timing error;
  octave-aware tempo error. Proposed release gates: F1 ≥ 0.90, median ≤ 25 ms,
  tempo error ≤ 3% on clean periodic fixtures. This is not a general music accuracy claim.
- Invariants: all references resolve; finite measurements; valid original-coordinate
  spans; deterministic IDs; schema round trips; chart and crop coordinates match audio.
- Counterfactuals: silence removes events; shifting audio shifts events; noise never
  establishes instrument identity; source questions abstain; unknown IDs fail explicitly.
- Systems: original checksum and sample rate preserved; cache avoids repeated analysis;
  concurrent analysis cannot expose partial artifacts; malformed uploads are rejected;
  localhost HTTP cannot read arbitrary files; tool errors preserve a usable service.
- Experience: import → analysis → playback/seek → section → sound/evidence → compare
  → download; keyboard and mobile layout; persistent library; failures and empty states.
- Integration: MCP initialize/list/call through a real SDK client; REST contract and CLI
  tests; build and run installed wheel, not only source checkout.

## Scientific boundaries

Structured evidence is a testable design decision, not a proven improvement over raw
audio. External-model ablations A/B/C/D/E, permissioned real-music listener annotations,
calibration, semantic models, separation, and BS.1770 loudness remain explicitly
unvalidated until their required datasets/model access exist. Ship an ablation result
format and grounded-answer scorer; never invent comparative results.

## Research grounding (checked 2026-11-06)

- Codebase: empty Git repository; no legacy behavior or dependencies to preserve.
- [Carone et al., PMLR 2026](https://proceedings.mlr.press/v303/carone26a.html)
  separates symbolic reasoning from audio perception. Supports explicit evidence;
  does not validate Muvi's extracted events or generalize a piano result to full mixes.
- [Dixit et al., 2024](https://arxiv.org/abs/2411.12058) studies spectrogram image
  classification. Supports keeping images as an audit view, not instrument ground truth.
- [librosa beat tracking documentation](https://librosa.org/doc/0.11.0/generated/librosa.beat.beat_track.html)
  and [Ellis's beat tracker](http://labrosa.ee.columbia.edu/projects/beattrack/)
  ground onset correlation and provisional beat alignment. Muvi uses a small SciPy
  implementation with bounded spectral blocks rather than a model runtime.
- [librosa maintainer/community discussion](https://groups.google.com/g/librosa/c/kQcdpryVEUU/m/JTzhEmxRAwAJ)
  and [BPM user reports](https://www.reddit.com/r/learnpython/comments/1j1afjl)
  inform failure cases (half/double tempo and temporal resolution), not accuracy claims.
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
  supplies the transport and tool schemas instead of a home-grown protocol.

No optional model weights or third-party music are bundled. Demo audio is synthesized
from original mathematical signals with reproducible seeds.

