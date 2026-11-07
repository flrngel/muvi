"""Explicit, atomic file exports outside the managed evidence library."""

import os
import tempfile
from pathlib import Path


def destination(path, engine, force=False, sources=()):
    path = Path(path).expanduser().absolute()
    resolved = path.resolve()
    if resolved.is_relative_to(engine.root) or path.is_symlink():
        raise ValueError("Export outside the managed library and do not target a symbolic link")
    if any(resolved == Path(source).resolve() for source in sources):
        raise ValueError("An export cannot replace its source audio")
    if path.exists():
        if not path.is_file():
            raise ValueError(f"Export destination is not a file: {path}")
        # Protect original audio even when the command uses an ID rather than a path.
        from genome.storage import checksum
        if path.stat().st_size <= 200 * 1024 * 1024:
            if checksum(path) in {t['track_id'].removeprefix('sha256:') for t in engine.list_tracks()}:
                raise ValueError("An export cannot replace original analyzed audio")
        if not force:
            raise FileExistsError(f"File exists: {path}. Choose another path or pass --force.")
    return path


def write(path, data, force=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if force:
            os.replace(temporary, path)
        else:
            # Atomic no-clobber publication on NTFS/POSIX, including concurrent writers.
            os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {"path": str(path), "uri": path.as_uri()}
