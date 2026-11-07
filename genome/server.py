"""One loopback service. Audio extraction runs in a single bounded worker."""

import asyncio
import json
import os
import sys
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.formparsers import MultiPartException

from genome import __version__
from genome.audio import MAX_UPLOAD_BYTES
from genome.engine import Engine
from genome.fixtures import synthesize
from genome.tools import MusicTools, SYSTEM_PROMPT


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    arguments: dict


class UploadLimitMiddleware:
    """Enforce the cap before the multipart parser can spool an unbounded body."""
    def __init__(self, app, limit):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") != "/api/upload":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = self.limit+1
        if length > self.limit:
            return await JSONResponse({"detail": "Audio exceeds the 200 MiB upload limit"}, status_code=413)(scope, receive, send)
        received = 0
        async def limited_receive():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > self.limit:
                # Starlette closes multipart temporary files when this exception is raised.
                raise MultiPartException("Audio exceeds the upload limit")
            return message
        await self.app(scope, limited_receive, send)


def create_app(root=None):
    engine = Engine(root)
    music = MusicTools(engine)
    jobs = {}
    guard = threading.Lock()
    worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="muvi-analysis")

    @asynccontextmanager
    async def lifespan(app):
        yield
        worker.shutdown(wait=True, cancel_futures=False)

    app = FastAPI(title="Muvi · Music Genome", version=__version__, lifespan=lifespan)
    app.state.engine, app.state.music = engine, music
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])
    app.add_middleware(UploadLimitMiddleware, limit=MAX_UPLOAD_BYTES + 1024*1024)

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Cross-origin requests are not allowed"}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Cross-site requests are not allowed"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        return response

    @app.exception_handler(KeyError)
    async def key_error(request, exc):
        return JSONResponse({"detail": str(exc.args[0])}, status_code=404)

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        message = "Invalid tool arguments" if isinstance(exc, ValidationError) else str(exc)
        return JSONResponse({"detail": message}, status_code=422)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__, "local_only": True}

    @app.get("/api/tracks")
    def tracks():
        return {"tracks": engine.list_tracks()}

    def reserve_job(title):
        with guard:
            if sum(j["status"] in ("queued", "running") for j in jobs.values()) >= 2:
                return None
            for key in list(jobs):
                if len(jobs) < 64:
                    break
                if jobs[key]["status"] not in ("queued", "running"):
                    del jobs[key]
            job_id = uuid.uuid4().hex
            jobs[job_id] = {"job_id": job_id, "title": title, "status": "queued", "progress": 0,
                            "stage": "Waiting to analyze", "track_id": None, "error": None}
            return job_id

    def run_analysis(job_id, path, title, demo=False):
        def update(stage, fraction):
            with guard:
                jobs[job_id].update(status="running", stage=stage, progress=fraction)
        try:
            if demo:
                update("Making an original example", 0.02)
                synthesize(path)
            result = engine.analyze(path, title, update)
            with guard:
                jobs[job_id].update(status="complete", progress=1, stage="Ready to explore", track_id=result.track_id)
        except Exception as exc:
            # Error details are local; unexpected implementation traces stay out of the UI.
            error = str(exc) if isinstance(exc, ValueError) else "Analysis failed. Check the audio and try again."
            with guard:
                jobs[job_id].update(status="failed", error=error, stage="Could not analyze audio")
        finally:
            path.unlink(missing_ok=True)

    @app.post("/api/upload", status_code=202)
    async def upload(file: UploadFile = File(...)):
        title = Path((file.filename or "Untitled audio").replace("\\", "/")).stem[:160]
        job_id = reserve_job(title)
        if job_id is None:
            await file.close()
            return JSONResponse({"detail": "Two tracks are already queued. Try again when one finishes."}, status_code=429)
        fd, name = tempfile.mkstemp(prefix="muvi-upload-", suffix=".audio")
        path = Path(name)
        submitted = False
        try:
            count = 0
            with os.fdopen(fd, "wb") as target:
                while block := await file.read(1024*1024):
                    count += len(block)
                    if count > MAX_UPLOAD_BYTES:
                        raise ValueError("Audio exceeds the 200 MiB file limit")
                    target.write(block)
            if not count:
                raise ValueError("Choose a non-empty audio file")
            worker.submit(run_analysis, job_id, path, title)
            submitted = True
            return {"job_id": job_id}
        finally:
            await file.close()
            if not submitted:
                path.unlink(missing_ok=True)
                with guard:
                    jobs.pop(job_id, None)

    @app.post("/api/demo", status_code=202)
    def demo():
        job_id = reserve_job("After hours · original demo")
        if job_id is None:
            return JSONResponse({"detail": "Analysis queue is full"}, status_code=429)
        fd, name = tempfile.mkstemp(prefix="muvi-demo-", suffix=".wav")
        os.close(fd)
        worker.submit(run_analysis, job_id, Path(name), "After hours · original demo", True)
        return {"job_id": job_id}

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        with guard:
            if job_id not in jobs:
                raise KeyError("Unknown analysis job")
            return dict(jobs[job_id])

    @app.get("/api/tracks/{track_id}")
    def track(track_id: str):
        return engine.load(track_id).model_dump()

    @app.get("/api/tracks/{track_id}/visuals")
    def visuals(track_id: str):
        g = engine.load(track_id)
        a = engine.arrays(track_id, g.analysis_id)
        # These arrays are for display. Full-resolution evidence stays in the NPZ artifact.
        step = max(1, int(np.ceil(len(a["times_s"])/900)))
        columns = range(0, len(a["times_s"]), step)
        def aggregate(data):
            return np.stack([data[..., i:i+step].mean(axis=-1) for i in columns], axis=-1)
        return {"analysis_id": g.analysis_id, "time_span": {"start_s": 0, "end_s": g.duration_s},
                "times_s": a["times_s"][::step].tolist(), "band_power": aggregate(a["band_power"]).tolist(),
                "onset_strength": aggregate(a["onset_strength"]).tolist(),
                "spectrogram_db": (10*np.log10(aggregate(a["spectrogram_power"])+1e-12)).round(1).tolist(),
                "frequency_edges_hz": a["frequency_edges_hz"].tolist(),
                "waveform": a["waveform"].tolist(), "waveform_times_s": a["waveform_times_s"].tolist(),
                "onset_times_s": a["times_s"][a["onset_frames"]].tolist(),
                "display_aggregation": "mean power per time bin; exact events retained"}

    @app.get("/api/tracks/{track_id}/export")
    def export(track_id: str):
        g = engine.load(track_id)
        return FileResponse(engine.directory(track_id, g.analysis_id)/"genome.json", media_type="application/json", filename="music-genome.json")

    @app.get("/api/tracks/{track_id}/artifacts/{artifact:path}")
    def artifact(track_id: str, artifact: str, analysis_id: str | None = None):
        g = engine.load(track_id, analysis_id)
        directory = engine.directory(track_id, g.analysis_id).resolve()
        path = (directory/artifact).resolve()
        if not path.is_relative_to(directory) or path.suffix not in (".wav", ".png", ".json", ".npz"):
            raise KeyError("Unknown artifact")
        if not path.is_file():
            raise KeyError("Artifact is not available")
        return FileResponse(path)

    @app.get("/api/tools")
    def tool_list():
        return {"tools": [{"name": name, "description": fn.__doc__, "input_schema": music.schemas(True)[name].model_json_schema()}
                          for name, fn in music.registry(True).items()], "system_prompt": SYSTEM_PROMPT,
                "mcp_config": {"mcpServers": {"muvi": {"command": sys.executable, "args": ["-m",
                    "genome.cli", "mcp", "--data-dir", str(engine.root)]}}}}

    @app.post("/api/tools/{name}")
    async def call_tool(name: str, body: ToolCall):
        return await asyncio.to_thread(music.call, name, body.arguments, True)

    static = Path(__file__).parent/"static"
    if static.exists():
        app.mount("/", StaticFiles(directory=static, html=True), name="workspace")
    return app

