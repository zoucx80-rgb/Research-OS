from research_os.domain.versions import VersionBundle
from research_os.version import CORE_API_VERSION


def test_core_api_version_is_stable_v1_contract():
    assert CORE_API_VERSION == "1.0"


def test_legacy_version_bundle_defaults_core_api_version_without_migration():
    bundle = VersionBundle.model_validate({
        "research_os_version": "1.2.1",
        "dataset_version": "dataset@test",
        "parser_version": "parser@test",
        "formula_version": "formula@test",
        "router_version": "router@test",
        "kpi_pack_version": "kpi@test",
        "driver_model_version": "driver@test",
        "forecast_version": "forecast@test",
        "valuation_version": "valuation@test",
        "report_version": "report@test",
    })
    assert bundle.core_api_version == CORE_API_VERSION
