from datetime import datetime, timezone

from research_os.plugins.models import ApplicabilityResult, PluginManifest
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolution
from research_os.reporting.contributions import ReportContribution
from research_os.runtime.result import ComponentFingerprint
from research_os.snapshots.service import SnapshotService


VERSIONS = {
    "research_os_version": "1.3.0",
    "dataset_version": "dataset@test",
    "parser_version": "parser@test",
    "formula_version": "formula@test",
    "router_version": "router@test",
    "kpi_pack_version": "kpi@test",
    "driver_model_version": "driver@test",
    "forecast_version": "forecast@test",
    "valuation_version": "valuation@test",
    "report_version": "report@test",
    "core_api_version": "1.0",
}


class NewerManufacturingPlugin:
    manifest = PluginManifest(
        plugin_id="industry:manufacturing",
        plugin_type="industry",
        plugin_version="1.1.0",
        api_version="1.0",
        min_research_os_version="1.3.0",
        provides={"kpi.metrics"},
        requires={"business_model.profile"},
        supported_business_models={"manufacturing"},
        maturity="stable",
    )

    def applicability(self, context):
        return ApplicabilityResult(applicable=True, score=1.0)

    def modules(self):
        return []

    def report_contributions(self):
        return [ReportContribution(contribution_id="new", section="KPIs", order=1, artifact_keys=["kpi.metrics"])]


def test_v1_3_snapshot_freezes_selected_component_fingerprints_and_strategy_resolution():
    service = SnapshotService()
    fingerprints = [
        ComponentFingerprint(component_id="core:research-engine", component_type="core", component_version="1.0.0", api_version="1.0"),
        ComponentFingerprint(component_id="industry:manufacturing", component_type="industry", component_version="1.0.0", api_version="1.0"),
    ]
    strategy = StrategyResolution(rationale=["selected industry:manufacturing"])
    snapshot = service.freeze(
        "synthetic:manufacturer",
        datetime(2026, 8, 29, tzinfo=timezone.utc),
        VERSIONS,
        payload={"kind": "runtime"},
        component_fingerprints=fingerprints,
        strategy_resolution=strategy,
    )

    ids = {item["component_id"] for item in snapshot.payload["component_fingerprints"]}
    assert ids == {"core:research-engine", "industry:manufacturing"}
    assert snapshot.payload["strategy_resolution"]["rationale"] == ["selected industry:manufacturing"]
    assert service.verify(snapshot.snapshot_id) is True


def test_snapshot_remains_reproducible_after_separate_registry_registers_newer_plugin():
    service = SnapshotService()
    snapshot = service.freeze(
        "synthetic:manufacturer",
        datetime(2026, 8, 29, tzinfo=timezone.utc),
        VERSIONS,
        component_fingerprints=[
            ComponentFingerprint(component_id="industry:manufacturing", component_type="industry", component_version="1.0.0", api_version="1.0")
        ],
        strategy_resolution=StrategyResolution(),
    )
    original_hash = snapshot.payload_hash

    newer_registry = PluginRegistry(core_api_version="1.0", research_os_version="1.3.0")
    newer_registry.register(NewerManufacturingPlugin())

    assert newer_registry.get("industry:manufacturing").manifest.plugin_version == "1.1.0"
    assert snapshot.payload["component_fingerprints"][0]["component_version"] == "1.0.0"
    assert snapshot.payload_hash == original_hash
    assert service.verify(snapshot.snapshot_id) is True


def test_historical_snapshot_payload_does_not_require_v1_3_fingerprint_keys():
    service = SnapshotService()
    snapshot = service.freeze(
        "synthetic:historical",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        {**VERSIONS, "research_os_version": "1.2.1"},
        payload={"legacy": True},
    )
    assert snapshot.payload == {"legacy": True}
    assert service.verify(snapshot.snapshot_id) is True
