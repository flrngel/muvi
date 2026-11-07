import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

from filelock import FileLock

from genome.config import ANALYSIS_SR, PARAMETERS
from genome.schema import Claim, Evidence, Genome
from genome.storage import checksum, publish_directory

PIPELINE_VERSION = "0.5.1"
PARAMETERS_SHA = hashlib.sha256(json.dumps(PARAMETERS, sort_keys=True).encode()).hexdigest()
ANALYSIS_ID = f"dsp-{PIPELINE_VERSION}-{PARAMETERS_SHA[:12]}"


def extract(audio):
    from genome.features import extract as compute
    return compute(audio)


class Engine:
    def __init__(self, root=None):
        self.root = Path(root or os.environ.get("MUVI_DATA_DIR", Path.home()/".muvi")).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def directory(self, track_id, analysis_id=None):
        digest = track_id.removeprefix("sha256:")
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid track ID")
        if analysis_id is not None:
            if not re.fullmatch(r"dsp-[a-zA-Z0-9._-]{1,100}", analysis_id):
                raise ValueError("Invalid analysis ID")
            return self.root/digest/analysis_id
        current = self.root/digest/ANALYSIS_ID
        if (current/"genome.json").exists():
            return current
        previous = sorted((self.root/digest).glob("dsp-*/genome.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return previous[0].parent if previous else current

    def load(self, track_id, analysis_id=None):
        path = self.directory(track_id, analysis_id)/"genome.json"
        if not path.is_file():
            raise KeyError("Track is not in this library; analyze it first")
        return Genome.model_validate_json(path.read_text(encoding="utf-8"))

    def arrays(self, track_id, analysis_id=None):
        import numpy as np
        with np.load(self.directory(track_id, analysis_id)/"arrays/features.npz", allow_pickle=False) as data:
            return {k: data[k] for k in data.files}

    def list_tracks(self):
        result = []
        seen = set()
        for path in sorted(self.root.glob("*/dsp-*/genome.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                track_hash = path.parent.parent.name
                if track_hash in seen:
                    continue
                g = self.load(track_hash)
                seen.add(track_hash)
                result.append({"track_id": g.track_id, "title": g.title, "duration_s": g.duration_s,
                               "tempo_bpm": g.tempo.preferred_bpm, "analysis_id": g.analysis_id,
                               "new_analysis_available": g.analysis_id != ANALYSIS_ID})
            except (ValueError, OSError):
                continue
        return result

    def analyze(self, path, title=None, progress=None):
        path = Path(path).resolve()
        if not path.is_file():
            raise ValueError("Audio file does not exist")
        # Check limits before hashing or copying an unbounded input.
        if path.stat().st_size > 200 * 1024 * 1024:
            raise ValueError("Audio exceeds the 200 MiB file limit")
        digest = checksum(path)
        track_id = f"sha256:{digest}"
        destination = self.directory(track_id, ANALYSIS_ID)
        destination.parent.mkdir(parents=True, exist_ok=True)
        report = progress or (lambda stage, fraction: None)
        with FileLock(str(destination.parent/"analysis.lock"), timeout=300):
            if (destination/"genome.json").exists():
                report("Loaded cached analysis", 1)
                return self.load(track_id, ANALYSIS_ID)
            report("Preparing local analysis", 0.01)
            import numpy as np
            import soundfile as sf
            from genome.audio import decode, source_metrics
            from genome.objects import index_objects
            from genome.structure import segment
            from genome.tempo import estimate
            from genome.rhythm import extract_rhythm
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
                metrics = source_metrics(pcm, sr)
                del pcm
                report("Measuring rhythm and frequency", 0.25)
                features = extract(mono)
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
                chroma = features["chroma_power"].mean(axis=1)
                chroma /= max(float(chroma.sum()), 1e-12)
                add("spectral_texture", 0, duration, "stft_chroma_and_median_texture_masks",
                    "Pitch-class energy and harmonic-like texture describe the mixture; no key or instrument is asserted.",
                    {"mean_chroma_fraction": chroma.tolist(),
                     "mean_harmonic_like_ratio": float(features["harmonic_like_ratio"].mean()),
                     "mean_centroid_hz": float(features["centroid_hz"].mean()),
                     "mean_spectral_flatness": float(features["flatness"].mean())},
                    {"mean_chroma_fraction": "relative energy ordered C,C#,D,D#,E,F,F#,G,G#,A,A#,B",
                     "mean_harmonic_like_ratio": "median-mask energy ratio, not probability",
                     "mean_centroid_hz": "Hz", "mean_spectral_flatness": "ratio"})
                report("Finding recurring sounds and changes", 0.65)
                sections = segment(features, duration, add)
                objects, occurrences, patterns = index_objects(features, duration, add)
                rhythm = extract_rhythm(features, duration, add)
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
                                parameters_sha256=PARAMETERS_SHA, tempo=tempo, rhythm=rhythm, sections=sections, sound_objects=objects,
                                occurrences=occurrences, patterns=patterns, claims=claims, evidence=evidence,
                                warnings=warnings, artifacts={"source_audio": "audio/source.wav", "original": "audio/original",
                                "arrays": "arrays/features.npz"}, elapsed_s=round(time.perf_counter()-started, 3))
                report("Saving your musical evidence", 0.92)
                np.savez_compressed(staging/"arrays/features.npz", **features)
                (staging/"genome.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
                (staging/"manifest.json").write_text(json.dumps({"analysis_id": ANALYSIS_ID,
                    "source_sha256": digest, "parameters_sha256": PARAMETERS_SHA,
                    "files": {str(p.relative_to(staging)).replace("\\", "/"): checksum(p)
                              for p in staging.rglob("*") if p.is_file()}}, indent=2), encoding="utf-8")
                publish_directory(staging, destination)
                report("Ready to explore", 1)
                return result
            finally:
                if staging.exists():
                    shutil.rmtree(staging)

