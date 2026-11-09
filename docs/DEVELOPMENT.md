# Development

From a checkout, with Python 3.12 or 3.13:

```sh
uv venv --python 3.12
uv pip install --python .venv --only-binary cryptography --group dev ".[mcp]"
uv run --no-sync python -m pytest -q
uv run --no-sync ruff check genome tests scripts
```

This installation resolves platform-compatible wheels. The existing development
lock may require a cryptography source build on Intel macOS when using
`uv sync --locked` instead.

Verification runs locally. GitHub Actions is disabled. See the
[platform results](PUBLICATION.md), [verification record](VERIFICATION.md),
[beat evaluation](REAL_BEAT_EVALUATION.md),
[whole-track and comparison evaluation](FLOW_COMPARISON_EVALUATION.md), and
[visual-output checks](VISUAL_OUTPUT_EVALUATION.md).

README images are actual CLI output hosted as release attachments. Generated
audio, images and archives stay outside Git history.

The package is `muvi-genome`; the command is `muvi`. `music-genome` is also available
as an alias. The package is not published on PyPI.
