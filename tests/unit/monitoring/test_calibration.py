import pytest
from research_os.monitoring.calibration import brier_score


def test_brier_score_for_binary_outcome():
    assert brier_score(0.7, 1) == pytest.approx(0.09)


def test_probability_is_bounded():
    with pytest.raises(ValueError):
        brier_score(1.2, 1)
