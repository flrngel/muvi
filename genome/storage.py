"""Lightweight content identity without decoding audio."""

import hashlib
import os
import time
from pathlib import Path


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def publish_directory(staging: Path, destination: Path):
    """Atomically publish, tolerating brief Windows handle contention for at most .75 s."""
    for attempt in range(5):
        try:
            os.replace(staging, destination)
            return
        except OSError as exc:
            if getattr(exc, 'winerror', None) not in (5, 32, 33) or attempt == 4:
                raise
            # The same permission checks still apply on every attempt. Never delete
            # the destination, publish partial files, or bypass a persistent error.
            time.sleep(.05*2**attempt)
