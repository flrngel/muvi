"""Canonical schema. Times are seconds in the original, untrimmed recording."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Status = Literal["observed", "inferred", "unresolved", "rejected"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Span(Model):
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_s <= self.start_s:
            raise ValueError("end_s must be greater than start_s")
        return self


class Tempo(Model):
    candidates_bpm: list[float] = []
    preferred_bpm: float | None = None
    candidate_scores: list[float] = []
    confidence_type: str = "uncalibrated_rank"
    status: Status = "unresolved"
    downbeat_status: str = "not_estimated"
    beat_times_s: list[float] = []
    limitation: str = "Half/double tempo and changing tempo may be ambiguous. Grid is provisional."


class Evidence(Span):
    id: str
    kind: str
    method: str
    method_version: str
    parameters_ref: str
    observation: str
    measurements: dict[str, float | list[float] | str | None]
    units: dict[str, str]
    measurement_status: Status = "observed"
    raw_ref: str = "arrays/features.npz"


class Section(Span):
    id: str
    structure_group: str
    functional_label: str | None = None
    status: Status = "inferred"
    evidence_ids: list[str]
    sound_object_ids: list[str] = []
    mean_band_power: list[float]
    onset_count: int


class Occurrence(Span):
    id: str
    sound_object_id: str
    similarity: float = Field(ge=0, le=1)
    similarity_type: str = "descriptor_cosine_not_probability"


class SoundObject(Model):
    id: str
    name: str
    form: str
    function_candidates: list[str]
    role_status: Status = "inferred"
    source_candidates: list[str] = ["unknown"]
    source_status: Status = "unresolved"
    mixture_status: str = "may_contain_overlapping_sources"
    fingerprint: dict[str, float]
    prototype_crop: Span
    evidence_ids: list[str]
    occurrence_pattern_ids: list[str] = []
    occurrence_count: int = 0


class Pattern(Model):
    id: str
    sound_object_id: str
    base_grid: str = "seconds"
    interval_s: float
    repeat_intervals: list[Span]
    repeat_count: int
    exceptions_s: list[float]
    alignment_status: str = "provisional"
    evidence_ids: list[str]


class Claim(Span):
    id: str
    question: str
    verdict: Literal["supported", "refuted", "indeterminate"]
    supporting_evidence_ids: list[str]
    alternatives: list[str]
    limitation: str


class Genome(Model):
    schema_version: str = "0.1.0"
    track_id: str
    analysis_id: str
    title: str
    duration_s: float = Field(gt=0)
    sample_rate: int
    channels: int
    source_sha256: str
    source_format: str
    analysis_sample_rate: int
    mono_policy: str
    pipeline_version: str
    parameters: dict[str, int | float | str | list[int]]
    parameters_sha256: str
    tempo: Tempo
    sections: list[Section]
    sound_objects: list[SoundObject]
    occurrences: list[Occurrence]
    patterns: list[Pattern]
    claims: list[Claim]
    evidence: list[Evidence]
    warnings: list[str]
    artifacts: dict[str, str]
    elapsed_s: float

    @model_validator(mode="after")
    def integrity(self):
        evidence_ids = {e.id for e in self.evidence}
        sound_ids = {s.id for s in self.sound_objects}
        pattern_ids = {p.id for p in self.patterns}
        entities = [*self.evidence, *self.sections, *self.sound_objects,
                    *self.occurrences, *self.patterns, *self.claims]
        if len({x.id for x in entities}) != len(entities):
            raise ValueError("Duplicate entity ID")
        spans = [*self.evidence, *self.sections, *self.occurrences, *self.claims]
        spans += [s.prototype_crop for s in self.sound_objects]
        spans += [span for p in self.patterns for span in p.repeat_intervals]
        if any(s.end_s > self.duration_s + 1e-6 for s in spans):
            raise ValueError("Evidence exceeds original audio duration")
        for entity in entities:
            refs = getattr(entity, "evidence_ids", getattr(entity, "supporting_evidence_ids", []))
            if not set(refs) <= evidence_ids:
                raise ValueError("Dangling evidence reference")
        if any(o.sound_object_id not in sound_ids for o in self.occurrences + self.patterns):
            raise ValueError("Dangling acoustic object reference")
        if any(not set(s.occurrence_pattern_ids) <= pattern_ids for s in self.sound_objects):
            raise ValueError("Dangling pattern reference")
        if any(not set(s.sound_object_ids) <= sound_ids for s in self.sections):
            raise ValueError("Dangling section object reference")
        if not self.sections or abs(self.sections[0].start_s) > 1e-6:
            raise ValueError("Sections must cover the track")
        if abs(self.sections[-1].end_s - self.duration_s) > 1e-6:
            raise ValueError("Sections must cover the track")
        if any(abs(a.end_s - b.start_s) > 1e-6 for a, b in zip(self.sections, self.sections[1:])):
            raise ValueError("Sections must be contiguous")
        return self

