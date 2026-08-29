import pytest

from research_os.kpi.finance_core import turnover_days


def test_h1_period_days_are_used_for_turnover_days():
    assert turnover_days(90.0, 110.0, 1000.0, {"period_type": "H1", "period_days": 181}) == pytest.approx(18.1)


def test_q1_q3_is_treated_as_cumulative_period():
    assert turnover_days(60.0, 90.0, 300.0, {"period_type": "Q1_Q3", "period_days": 274}) == pytest.approx(68.5)


def test_interim_period_without_length_does_not_fall_back_to_365():
    assert turnover_days(90.0, 110.0, 1000.0, {"period_type": "H1"}) is None


def test_fy_with_leap_year_dates_uses_366_days():
    assert turnover_days(
        90.0,
        110.0,
        1000.0,
        {"period_type": "FY", "period_start": "2028-01-01", "period_end": "2028-12-31"},
    ) == pytest.approx(36.6)


def test_fy_without_period_metadata_preserves_365_day_compatibility():
    assert turnover_days(90.0, 110.0, 1000.0) == pytest.approx(36.5)
