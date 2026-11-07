# Beat understanding: preregistered evaluation (0.4.0 baseline)

Requested: independent Terra and Luna agents must use Muvi as MCP/CLI consumers,
answer actual rhythm questions, expose failures, and retest improvements.

## Isolation and protocol

- Freeze commit 301d476 as the baseline. Terra uses real MCP stdio; Luna uses the CLI
  as an agent skill. Both start without parent history and may inspect only public
  documentation, schema and tool outputs, not DSP code, synthesis truth or each other.
- Root owns truth, scoring, tuning and integration. Agents record calls, answers and
  uncertainty separately. This is a small paired case study, not a model leaderboard.
- Eight development recordings cover steady pulse, missing attacks, abrupt/gradual
  tempo changes, a silent break, stationary noise, swing subdivisions and dominant
  bright subdivisions. Eight held-out recordings use different rates, seeds and offsets.
- Truth is deterministic generated audio, with exact onset samples and known pulse
  intervals. No real-music accuracy or subjective beat/meter ground truth is claimed.
- First collect answers on the frozen baseline. Tune only using development failures.
  Freeze the implementation before exposing held-out cases or inspecting their results.
  Both agents answer held-out cases through both the old and new tool surface; report
  the within-agent learning/order limitation instead of claiming independent trials.

## Questions and scoring fixed before collecting answers

For each anonymous case: whether a regular low-frequency transient pulse is established;
its physical attack rate in two specified windows; first five low-pulse attack times;
onset-free gaps longer than two seconds between the first and last low-pulse attack;
whether meter/downbeat and an independent bass source can be established.

- Pulse presence: exact Boolean, or null if the evidence is inadequate (miss on a
  generated periodic pulse, correct on noise only when false).
- Each local pulse rate: within 5% of the generated rate, without half/double credit.
  This asks for acoustic attack rate, not the uniquely correct perceived musical tempo.
- First five attacks: one-to-one match within 50 ms, F1 >= 0.90; empty on noise.
- Long gaps: onset-free interval endpoints within 120 ms; no invented gaps.
- Meter/downbeat and independent bass: indeterminate. Source identity is not proven
  by the synthesis recipe, which the models do not see.
- Grounding: actual retrieved evidence IDs, track/analysis IDs and original spans.
  Missing/unknown IDs do not earn citation credit. Preserve model answers verbatim.

Report per-component accuracy and raw counts; do not hide weaknesses inside a single
aggregate. Compare pipeline event timing and spurious grid events in silent spans too.
Human-readable audit reports supplement automatic scoring of structured responses.

## Implementation acceptance

Address observed defects with versioned evidence and bounded retrieval, preserving
uncertainty and original timestamps. Verify every new tool through CLI and actual MCP;
retain existing regression checks, old-library compatibility, build/installed-wheel
smoke tests, and subprocess cleanup. Bump the package/pipeline version and commit each
completed implementation using Conventional Commits. Record actual failures as well
as final results. Root alone updates the td task.

## Post-evaluation reliability verification (added after observing failures)

Both held-out MCP conditions encountered a transient Windows access-denied error
while atomically renaming a completed staging directory. Each recovered on the
consumer's next attempt. Preserve those failures and call counts in the report.
After all answers are frozen, add bounded retries for Windows sharing/access errors
at this publication boundary. Test a real non-delete-sharing Windows directory
handle, permanent-error propagation, and no retry of unrelated errors. Do not change
rhythm math based on held-out truth; compare final rhythm outputs to the evaluated
snapshot and keep the two implementation versions explicit.
