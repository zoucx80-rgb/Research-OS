from research_os.router.models import BusinessModelProfile
from research_os.kpi.base import KpiPackRegistry

def test_distributor_profile_loads_core_and_distributor():
    packs=KpiPackRegistry.default().resolve(BusinessModelProfile(company_id="X",primary_model="distributor",confidence=.9,evidence_ids=["e1"],router_version="router@1.0.0"))
    assert [p.pack_id for p in packs]==["core","distributor"]

def test_kpi_packs_expose_versioned_data_contract_metadata():
    from research_os.kpi.distributor import DistributorPack
    from research_os.kpi.manufacturing import ManufacturingPack
    d=DistributorPack(); m=ManufacturingPack()
    assert {'revenue','cogs'} <= set(d.required_facts)
    assert d.missing_policy=='preserve_missing'
    assert 'distributor' in d.eligible_business_models
    assert 'manufacturing' in m.eligible_business_models
    assert m.required_facts
