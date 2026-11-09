import pytest

from scripts.score_real_beats import match_beats


def test_reference_scoring_does_not_forgive_subdivisions_or_phase_shift():
    reference = [1, 1.5, 2, 2.5]
    exact = match_beats(reference, [1.02, 1.48, 2.01, 2.49])
    assert exact['f1'] == 1 and exact['median_error_s'] == pytest.approx(.015)
    double = match_beats(reference, [1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75])
    assert double['precision'] == .5 and double['recall'] == 1
    assert match_beats(reference, [1.25, 1.75, 2.25, 2.75])['f1'] == 0
    duplicate = match_beats([1], [1, 1.01])
    assert duplicate['matches'] == 1 and duplicate['precision'] == .5
    assert match_beats(reference, [])['f1'] == 0
