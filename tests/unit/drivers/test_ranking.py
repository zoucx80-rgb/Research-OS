import pytest
from research_os.drivers.ranking import ScoredDriver, rank_drivers


def test_priority_is_product_of_four_components():
    ranked = rank_drivers(
        [
            ScoredDriver(
                driver_id="a",
                materiality=0.9,
                uncertainty=0.8,
                observability=0.7,
                decision_relevance=0.6,
            ),
            ScoredDriver(
                driver_id="b",
                materiality=0.5,
                uncertainty=0.5,
                observability=1,
                decision_relevance=1,
            ),
        ]
    )
    assert ranked[0].driver_id == "a"
    assert ranked[0].score == pytest.approx(0.9 * 0.8 * 0.7 * 0.6)
