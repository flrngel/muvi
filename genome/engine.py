import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from filelock import FileLock

from genome.audio import ANALYSIS_SR, checksum, decode, source_metrics
from genome.features import PARAMETERS, extract
from genome.objects import index_objects
from genome.schema import Claim, Evidence, Genome
from genome.structure import segment
from genome.tempo import estimate

PIPELINE_VERSION = "0.2.0"
PARAMETERS_SHA = hashlib.sha256(json.dumps(PARAMETERS, sort_keys=True).encode()).hexdigest()
ANALYSIS_ID = f"dsp-{PIPELINE_VERSION}-{PARAMETERS_SHA[:12]}"


class Engine:
    def __init__(self, root=None):
        self.root = Path(root or os.environ.get("MUVI_DATA_DIR", Path.home()/".muvi")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def directory(self, track_id):
        digest = track_id.removeprefix("sha256:")
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid track ID")
        return self.root/digest/ANALYSIS_ID

    def load(self, track_id):
        path = self.directory(track_id)/"genome.json"
        if not path.is_file():
            raise KeyError("Track is not in this library; analyze it first")
        return Genome.model_validate_json(path.read_text(encoding="utf-8"))

    def arrays(self, track_id):
        with np.load(self.directory(track_id)/"arrays/features.npz", allow_pickle=False) as data:
            return {k: data[k] for k in data.files}

    def list_tracks(self):
        result = []
        for path in sorted(self.root.glob(f"*/{ANALYSIS_ID}/genome.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                g = Genome.model_validate_json(path.read_text(encoding="utf-8"))
                result.append({"track_id": g.track_id, "title": g.title, "duration_s": g.duration_s,
                               "tempo_bpm": g.tempo.preferred_bpm, "analysis_id": g.analysis_id})
            except (ValueError, OSError):
                continue
        return result

    def analyze(self, path, title=None, progress=None):
        path = Path(path).resolve()
        if not path.is_file():
            raise ValueError("Audio file does not exist")
        # Check limits before hashing or copying an unbounded input.
        from genome.audio import MAX_UPLOAD_BYTES
        if path.stat().st_size > MAX_UPLOAD_BYTES:
            raise ValueError("Audio exceeds the 200 MiB file limit")
        digest = checksum(path)
        track_id = f"sha256:{digest}"
        destination = self.directory(track_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        report = progress or (lambda stage, fraction: None)
        with FileLock(str(destination.parent/"analysis.lock"), timeout=300):
            if (destination/"genome.json").exists():
                report("Loaded cached analysis", 1)
                return self.load(track_id)
            started = time.perf_counter()
            staging = Path(tempfile.mkdtemp(prefix=".analysis-", dir=destination.parent))
            try:
                for folder in ("audio", "arrays", "images", "clips"):
                    (staging/folder).mkdir()
                # Decode the exact bytes whose hash forms the cache key, even if the caller changes its file.
                shutil.copyfile(path, staging/"audio/original")
                if checksum(staging/"audio/original") != digest:
                    raise ValueError("Audio changed while it was being imported; retry")
                report("Reading original audio", 0.08)
                pcm, sr, mono, policy, source_format = decode(staging/"audio/original")
                duration = len(pcm)/sr
                sf.write(staging/"audio/source.wav", pcm, sr, subtype="DOUBLE")
                sf.write(staging/"audio/preview.wav", pcm, sr, subtype="PCM_16")
                metrics = source_metrics(pcm, sr)
                del pcm
                report("Measuring rhythm and frequency", 0.25)
                features = extract(mono)
                # Exact waveform peaks are a display artifact, not evidence of individual sources.
                step = max(1, int(np.ceil(len(mono)/1200)))
                features["waveform"] = np.array([np.max(np.abs(mono[i:i+step])) for i in range(0, len(mono), step)])
                features["waveform_times_s"] = np.arange(len(features["waveform"]))*step/ANALYSIS_SR
                del mono
                evidence = []
                def add(kind, start, end, method, observation, measurements, units):
                    ev = Evidence(id=f"E{len(evidence)+1:04}", kind=kind, start_s=start, end_s=end,
                                  method=method, method_version=PIPELINE_VERSION, parameters_ref=PARAMETERS_SHA,
                                  observation=observation, measurements=measurements, units=units)
                    evidence.append(ev)
                    return ev
                add("source_metrics", 0, duration, "original_rate_pcm_statistics",
                    "Sample peak and RMS are measured at source rate. LUFS and true peak are not measured.",
                    metrics, {"sample_peak_dbfs": "dBFS sample peak", "rms_dbfs": "dBFS RMS", "crest_db": "dB",
                              "samples_at_or_above_full_scale": "samples across channels", "stereo_correlation": "Pearson r",
                              "side_to_total_energy": "ratio", "measurement_sample_rate": "Hz",
                              "integrated_lufs": "not measured", "true_peak_dbtp": "not measured"})
                tempo = estimate(features, duration)
                add("rhythm", 0, duration, "short_stft_flux_autocorrelation",
                    "Transient onsets and provisional periodicity, with octave alternatives.",
                    {"onset_count": float(len(features["onset_frames"])), "tempo_candidates_bpm": tempo.candidates_bpm},
                    {"onset_count": "events", "tempo_candidates_bpm": "beats/min, inferred"})
                report("Finding recurring sounds and changes", 0.65)
                sections = segment(features, duration, add)
                objects, occurrences, patterns = index_objects(features, duration, add)
                for section in sections:
                    section.sound_object_ids = sorted({o.sound_object_id for o in occurrences
                                                       if o.start_s < section.end_s and o.end_s > section.start_s})
                claims = [Claim(id="C01", question="Is the low end an independent bass or a pulse tail?",
                                start_s=0, end_s=duration, verdict="indeterminate",
                                supporting_evidence_ids=[e.id for e in evidence if e.kind == "low_sustain"],
                                alternatives=["independent bass layer", "reverberant or distorted pulse tail", "overlapping mixture"],
                                limitation="Band activity and recurrence cannot establish production-source identity.")]
                warnings = ["Acoustic objects may contain overlapping sources; roles and section groups are provisional.",
                            "Analysis bands stop at 11,025 Hz; these are not full-band mastering measurements."]
                if policy != "channel_mean":
                    warnings.append("Stereo cancellation detected; structural features use the highest-energy channel.")
                if not len(features["onset_frames"]):
                    warnings.append("No salient transient events detected; a beat grid may be unavailable.")
                result = Genome(track_id=track_id, analysis_id=ANALYSIS_ID, title=title or path.stem,
                                duration_s=duration, sample_rate=sr, channels=sf.info(staging/"audio/source.wav").channels,
                                source_sha256=digest, source_format=source_format, analysis_sample_rate=ANALYSIS_SR,
                                mono_policy=policy, pipeline_version=PIPELINE_VERSION, parameters=PARAMETERS,
                                parameters_sha256=PARAMETERS_SHA, tempo=tempo, sections=sections, sound_objects=objects,
                                occurrences=occurrences, patterns=patterns, claims=claims, evidence=evidence,
                                warnings=warnings, artifacts={"source_audio": "audio/source.wav", "original": "audio/original",
                                "browser_audio": "audio/preview.wav",
                                "arrays": "arrays/features.npz"}, elapsed_s=round(time.perf_counter()-started, 3))
                report("Saving your musical evidence", 0.92)
                np.savez_compressed(staging/"arrays/features.npz", **features)
                (staging/"genome.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
                (staging/"manifest.json").write_text(json.dumps({"analysis_id": ANALYSIS_ID,
                    "source_sha256": digest, "parameters_sha256": PARAMETERS_SHA,
                    "files": {str(p.relative_to(staging)).replace("\\", "/"): checksum(p)
                              for p in staging.rglob("*") if p.is_file()}}, indent=2), encoding="utf-8")
                os.replace(staging, destination)
                report("Ready to explore", 1)
                return result
            finally:
                if staging.exists():
                    shutil.rmtree(staging)

