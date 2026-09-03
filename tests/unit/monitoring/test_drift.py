from research_os.monitoring.drift import detect_business_model_drift


def test_material_business_mix_change_requests_router_review():
    a = detect_business_model_drift(
        {"distributor_score": 0.92, "manufacturer_score": 0.08},
        {"distributor_score": 0.55, "manufacturer_score": 0.45},
        threshold=0.25,
    )
    assert a.requires_router_review is True
