"""Explicit, atomic file exports outside the managed evidence library."""

import os
import tempfile
import hashlib
from pathlib import Path

from filelock import FileLock


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


def export_pair(output, result, engine, force, sources):
    if output.suffix.lower() != ".png":
        raise ValueError("Use a .png output file for render-pair")
    paths = {"passage":output, "phrase":output.with_name(output.stem+"-phrase.png"),
             "hits":output.with_name(output.stem+"-hits.png"), "legend":output.with_suffix(".json")}
    # Exports with intersecting names serialize, including from different libraries.
    key = hashlib.sha256(os.path.normcase(str(output.parent.resolve())).encode()).hexdigest()
    lock = Path(tempfile.gettempdir())/f"muvi-pair-export-{key}.lock"
    with FileLock(str(lock), timeout=120):
        paths = {k:destination(v, engine, force, sources) for k,v in paths.items()}
        paths["passage"].parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=paths["passage"].parent) as temp:
            written = {}
            try:
                for name, path in paths.items():
                    if path.exists():
                        os.link(path, Path(temp)/name)
                    written[name] = write(path, Path(result[name]["path"]).read_bytes(), force)
            except OSError:
                for name in reversed(written):
                    backup = Path(temp)/name
                    if backup.exists():
                        os.replace(backup, paths[name])
                    else:
                        paths[name].unlink()
                raise
        return written
