# Public release 0.8.3

Historical verification record. Starting with 0.8.4, GitHub Actions is disabled
and the workflow is removed. The README installs directly from Git `main`;
verification is performed locally when making changes.

## Acceptance checks

Before publishing: audit tracked files and nested trace archives, preserve numeric
evaluation values, check README relative links, package the generated demo chart,
validate the CI workflow, and smoke-test the built wheel outside the checkout.
After publishing: verify anonymous access, install from the exact README release
URL in a fresh tool environment, run the demo/window/comparison/chart workflow,
check the actual GitHub CI results, and verify release assets and their hashes.

## Public snapshot

The first public commit is a cleaned snapshot. Earlier evaluation documents retain
their local development commit IDs; those IDs are not ancestors of public `main`.
The local development history and original records remain available to the owner.

Machine-local usernames and path roots in exported evaluation records, including
the archived tool traces, are replaced with generic locations. Musical claims,
numbers, timestamps and input hashes are retained. Historical file hashes describe
the original pre-publication records, not the redacted copies. No evaluation audio,
local libraries, environments, credentials or private task records are published.

## Platform status

The [completed CI run](https://github.com/flrngel/muvi/actions/runs/42594074887)
passed on November 9, 2026, at
[`7a18733`](https://github.com/flrngel/muvi/commit/7a18733feb1537e8504bf263ebc391b155d464fa).
All five jobs passed lint, tests including actual MCP calls, and a built core-wheel
smoke test outside the checkout. Subsequent release changes only update documentation.

| GitHub-hosted runner | Python | Tests | Isolated core-wheel smoke |
| --- | --- | --- | --- |
| macOS 15, Apple Silicon | 3.12 | 102 passed, 1 skipped | Passed |
| macOS 15, Apple Silicon | 3.13 | 102 passed, 1 skipped | Passed |
| macOS 15, Intel | 3.12 | 102 passed, 1 skipped | Passed |
| Ubuntu 24.04 | 3.12 | 102 passed, 1 skipped | Passed |
| Windows 2025 | 3.12 | 103 passed | Passed |

The skipped test exercises Windows-specific file locking. macOS 13 binary
dependency checks previously passed for Apple Silicon/Intel and Python 3.12/3.13;
those checks were dependency resolution, not execution on macOS 13. The runtime
results above are hosted runners, not a test of every user's hardware or audio.

The [first CI run](https://github.com/flrngel/muvi/actions/runs/42593736713) failed
during test collection because the `pytest` entrypoint did not put the checkout
on the import path. Switching to `python -m pytest` fixed collection on all five
jobs; no application or DSP changes were needed.

## Fresh installation

On Windows, a separate temporary tool environment installed the first public
commit directly from its GitHub ZIP. `muvi --version` returned `0.8.3` and the
README demo, overview, 8–16 second window, comparison, beats and PNG render all
passed. Installing the optional MCP extra from the same URL then passed a real
stdio handshake, discovery of 16 tools, and `list_tracks`. The temporary library,
tool environment and MCP process were closed and removed after verification.

After publishing [v0.8.3](https://github.com/flrngel/muvi/releases/tag/v0.8.3), the
exact README tag URL passed the same fresh-environment CLI and MCP sequence again.
All four release assets were downloaded without authentication; the wheel, source
distribution and skill ZIP matched the published SHA-256 checksums. The skill ZIP
contains the same `muvi/SKILL.md` as the repository. No temporary server or tool
environment was retained.

The built wheel also passed the isolated core smoke locally. These checks cover
installation and the documented workflow; earlier music evaluations describe the
limits of beat and structural interpretation.
