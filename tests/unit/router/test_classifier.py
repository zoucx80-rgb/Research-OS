from datetime import datetime, timezone
from research_os.domain.evidence import Evidence
from research_os.router.classifier import BusinessModelRouter

def ev(metric,value):
    return Evidence(evidence_id=metric,company_id="001287.SZ",evidence_type="calculated_metric",
        publish_ts=datetime(2026,8,25,tzinfo=timezone.utc),ingested_at=datetime(2026,8,25,tzinfo=timezone.utc),
        value=value,source_table=metric,confidence_grade="B",verification_status="PRIMARY_VERIFIED")

def test_router_classifies_high_inventory_low_fixed_asset_company_as_distributor():
    profile=BusinessModelRouter().classify("001287.SZ",[
        ev("inventory_to_revenue",0.28),ev("fixed_asset_to_assets",0.01),ev("gross_margin",0.03),
        ev("business_description","electronic component distribution")])
    assert profile.primary_model=="distributor"
    assert profile.confidence>=0.80
    assert profile.evidence_ids
