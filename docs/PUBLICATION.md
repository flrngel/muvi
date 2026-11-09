# Public release 0.8.3

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

The 0.8.2 runtime baseline passed 103 tests on Windows and installed-wheel smoke.
macOS 13 binary dependency checks previously passed for Apple Silicon/Intel and
Python 3.12/3.13. Those resolution checks were not runtime tests.

The public CI matrix exercises Windows 2025, Ubuntu 24.04, macOS 15 Apple Silicon
and macOS 15 Intel with Python 3.12, plus Apple Silicon with Python 3.13. Each job
runs tests including actual MCP and an isolated core-wheel smoke. See the
[workflow runs](https://github.com/flrngel/muvi/actions/workflows/ci.yml) for live
status; scheduled jobs are not reported as successful runs here.
