import json
from pathlib import Path

import research_os
from research_os.release.runtime import CHECKS
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


ARCHITECTURE_GATES = {
    "research_context_contract",
    "research_inputs_contract",
    "module_contract",
    "pipeline_dependency_resolution",
    "plugin_manifest_contract",
    "plugin_compatibility_resolution",
    "industry_auto_resolution",
    "methodology_auto_resolution",
    "unsupported_coverage_gap",
    "plugin_failure_isolation",
    "canonical_runtime_entrypoint",
    "canonical_result_contract",
    "knowledge_interface_pit",
    "snapshot_component_fingerprints",
    "completion_single_source_v1_4",
    "core_api_version_consistency",
    "extensibility_no_engine_change",
    "no_legacy_runtime_policy_duplication",
}


def test_public_release_version_and_core_api_are_consistent():
    metadata = json.loads(Path("research_os_version.json").read_text())

    assert tuple(map(int, RESEARCH_OS_VERSION.split("."))) >= (1, 4, 0)
    assert RESEARCH_OS_VERSION == research_os.__version__
    assert metadata["research_os_version"] == RESEARCH_OS_VERSION
    assert CORE_API_VERSION == "1.0"
    assert metadata.get("core_api_version", "1.0") == "1.0"


def test_release_gate_contains_all_v1_4_architecture_checks():
    assert ARCHITECTURE_GATES.issubset(CHECKS)
    for gate in ARCHITECTURE_GATES:
        nodeid = CHECKS[gate]
        test_path = Path(nodeid.split("::", 1)[0])
        assert test_path.exists(), f"{gate} points to missing test: {test_path}"


def test_v1_4_release_documentation_contract_exists():
    plugin_authoring = Path("docs/architecture/plugin-authoring-v1.md")
    migration = Path("docs/migrations/v1.4.0.md")
    readme = Path("README.md").read_text()
    changelog = Path("CHANGELOG.md").read_text()
    prompt = Path("docs/prompts/stock_research.md").read_text()

    assert plugin_authoring.exists()
    assert migration.exists()
    assert "1.4.0" in readme
    assert "1.4.0" in changelog
    assert "plugin" in prompt.lower()
    assert "coverage gap" in prompt.lower() or "coverage_gap" in prompt.lower()


def test_legacy_policy_entrypoint_is_absent():
    assert not Path("src/research_os/orchestration.py").exists()
