from research_os.events.engine import ResearchEvent, EventEngine


def test_financing_event_maps_to_funding_drivers():
    i = EventEngine().map_impact(
        ResearchEvent(event_type="share_issue", company_id="X", payload={"amount": 3.0})
    )
    assert "financing" in i.affected_driver_types
    assert i.materiality in {"medium", "high"}
    assert i.next_required_check
