import pytest
from research_os.peers.normalization import ComparableMetric, normalize_peer_metric, PeerNormalizationError

def test_peer_comparison_rejects_h1_vs_fy_without_normalization():
    with pytest.raises(PeerNormalizationError):
        normalize_peer_metric(ComparableMetric(value=1,period_type="H1",scope="parent",accounting_definition="roe",frequency="semiannual",share_count_convention="weighted",business_model_interpretation="manufacturer"),
                              ComparableMetric(value=1,period_type="FY",scope="consolidated",accounting_definition="roe",frequency="annual",share_count_convention="weighted",business_model_interpretation="manufacturer"))
