# Overall and interval understanding: verify before changing

Baseline: d30112e / Muvi 0.6.0. User scope: improve the reusable skill and verify
independent agents actually understand whole tracks and arbitrary intervals.
Apply Occam's razor: reuse measured evidence and existing commands, add a retrieval
primitive only for an observed gap. No new audio model, UI or beat retuning planned.

1. Freeze baseline code/skill. Fresh Terra and Luna use only the public skill and
   commands to answer the same natural whole-track/interval questions. Give no
   expected answers, suspected defects or implementation. Preserve calls and answers.
2. Development: one anonymous controlled arrangement (known changes, repeating
   texture, a sustained middle and silence) plus one real NCS track already local.
   Ask overall evolution, arbitrary non-section-aligned spans, changes between
   spans, local versus global rhythm and source/meter uncertainty. Keep questions
   transport-independent; consumers choose their tools.
3. Score correctness, scope/timestamps, retrieved provenance and unnecessary calls.
   Synthetic answers can be checked against construction; real-track answers are
   checked for support/contradictions, not unsupported perceptual truth. Abstaining
   on a question that the measurements can answer is incomplete, not a success.
4. Patch only failures supported by code and independent use. Prefer a concise
   overall-to-detail skill, bounded summaries and exact-span measurements. Freeze
   the revised skill/runtime before fresh consumer testing on held-out cases.
5. Held-out: independently generated arrangement with reordered material, different
   tempo/durations, plus a different local NCS song. Fresh agents receive neither
   development answers nor scoring feedback. Report every question, misses,
   omissions and false claims; no confidence/accuracy equivalence.
6. Verify interval correctness at nonaligned boundaries, whole-track aggregation,
   pagination/truncation, silence, evidence, cache compatibility, real CLI/MCP and
   installed package/skill. Preserve old DSP outputs. Bump package for this work,
   commit with Conventional Commits, and close subprocesses.

Acceptance: all three comparison questions per synthetic case have the correct
direction with exact spans; correct broad order/repetition/silence without invented
instrument/meter labels; every numeric claim traceable to a retrieved response;
no silent substitution of candidate sections for user intervals. Report real-music
grounding separately from synthetic correctness. Do not add features to improve a
benchmark number unless they also solve an observed user workflow failure.
