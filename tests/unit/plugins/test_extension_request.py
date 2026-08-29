import inspect

from research_os.plugins.models import CoverageGap, ExtensionRequest
from research_os.plugins.registry import PluginRegistry


def test_coverage_gap_can_be_serialized_as_safe_extension_request_without_registry_mutation_path():
    request = ExtensionRequest(
        company_id="synthetic:unsupported",
        business_model="consumer",
        coverage_gaps=[CoverageGap(
            gap_type="industry_strategy",
            business_model="consumer",
            reason="no compatible stable industry strategy",
        )],
        evidence_requirements=["industry KPI definitions"],
        requested_capabilities=["kpi.metrics"],
    )
    payload = request.model_dump(mode="json")
    assert payload["business_model"] == "consumer"
    assert payload["coverage_gaps"][0]["gap_type"] == "industry_strategy"

    public_methods = {
        name: member
        for name, member in inspect.getmembers(PluginRegistry, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert "register" in public_methods
    assert all("ExtensionRequest" not in str(inspect.signature(method)) for method in public_methods.values())
