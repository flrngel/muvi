from genome.evaluate import onset_metrics, score_answers
from genome.engine import Engine
from genome.fixtures import synthesize


def test_one_to_one_onsets_penalize_duplicate_predictions():
    result = onset_metrics([1, 2], [1, 1.01, 2])
    assert result["recall"] == 1
    assert result["precision"] == 2/3


def test_grounding_scorer_rejects_missing_invented_and_out_of_span_claims(tmp_path):
    path = tmp_path/"a.wav"
    synthesize(path, kind="pulse", duration=4)
    engine = Engine(tmp_path/"store")
    g = engine.analyze(path)
    dataset = [{"question_id": "q1", "track_id": g.track_id, "time_span": {"start_s": 1, "end_s": 3},
                "expected_verdict": "indeterminate", "supporting_evidence_ids": ["E0002"]}]
    answer = {"question_id": "q1", "verdict": "indeterminate", "evidence_ids": ["E0002"],
              "time_spans": [{"start_s": 1, "end_s": 2}]}
    assert score_answers(engine, dataset, [answer])["grounded_verdict_accuracy"] == 1
    assert score_answers(engine, dataset, [dict(answer, evidence_ids=["fake"])])["grounded_verdict_accuracy"] == 0
    assert score_answers(engine, dataset, [dict(answer, time_spans=[{"start_s": 0, "end_s": 4}])])["grounded_verdict_accuracy"] == 0
    assert score_answers(engine, dataset, [])["grounded_verdict_accuracy"] == 0

