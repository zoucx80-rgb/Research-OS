import pytest
from research_os.drivers.ranking import ScoredDriver, rank_drivers

def test_priority_is_product_of_four_components():
    ranked=rank_drivers([ScoredDriver(driver_id="a",materiality=.9,uncertainty=.8,observability=.7,decision_relevance=.6),
                         ScoredDriver(driver_id="b",materiality=.5,uncertainty=.5,observability=1,decision_relevance=1)])
    assert ranked[0].driver_id=="a"
    assert ranked[0].score==pytest.approx(.9*.8*.7*.6)
