from research_os.router.models import BusinessModelProfile
from research_os.kpi.base import KpiPackRegistry

def test_distributor_profile_loads_core_and_distributor():
    packs=KpiPackRegistry.default().resolve(BusinessModelProfile(company_id="X",primary_model="distributor",confidence=.9,evidence_ids=["e1"],router_version="router@1.0.0"))
    assert [p.pack_id for p in packs]==["core","distributor"]
