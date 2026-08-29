from research_os.kpi.base import KpiPackRegistry
from research_os.orchestration import ResearchOS
from research_os.router.models import BusinessModelProfile


def profile(primary, secondary=None):
    return BusinessModelProfile(
        company_id="synthetic",
        primary_model=primary,
        secondary_models=secondary or [],
        confidence=.9,
        evidence_ids=["e1"],
        router_version="router@test",
    )


def test_distributor_has_specialized_kpi_support():
    resolution = KpiPackRegistry.default().resolve_with_status(profile("distributor"))
    assert [p.pack_id for p in resolution.specialized_packs] == ["distributor"]
    assert resolution.primary_supported is True
    assert ResearchOS._kpi_status(resolution) == "PASS"


def test_manufacturing_has_specialized_kpi_support():
    resolution = KpiPackRegistry.default().resolve_with_status(profile("manufacturing"))
    assert [p.pack_id for p in resolution.specialized_packs] == ["manufacturing"]
    assert resolution.primary_supported is True


def test_core_pack_only_never_counts_as_specialized_support():
    resolution = KpiPackRegistry.default().resolve_with_status(profile("consumer"))
    assert [p.pack_id for p in resolution.specialized_packs] == []
    assert "consumer" in resolution.unsupported_models
    assert resolution.primary_supported is False
    assert ResearchOS._kpi_status(resolution) == "INSUFFICIENT_EVIDENCE"


def test_unsupported_secondary_model_is_recorded_without_invalidating_supported_primary():
    resolution = KpiPackRegistry.default().resolve_with_status(profile("distributor", ["software"]))
    assert resolution.primary_supported is True
    assert "software" in resolution.unsupported_models
    assert ResearchOS._kpi_status(resolution) == "PASS"


def test_legacy_resolve_still_returns_core_and_supported_pack():
    packs = KpiPackRegistry.default().resolve(profile("distributor"))
    assert [p.pack_id for p in packs] == ["core", "distributor"]
