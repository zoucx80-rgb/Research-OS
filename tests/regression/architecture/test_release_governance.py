from __future__ import annotations

import ast
import json
from pathlib import Path
import tomllib

import research_os
from research_os.release.gate import REQUIRED
from research_os.release.manifest import CURRENT_RELEASE
from research_os.release.replays import REPLAY_REGISTRY, resolve_replay_profiles
from research_os.release.verification import resolve_release_checks
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


def test_build_safe_version_leaf_is_the_single_product_identity_source():
    assert research_os.__version__ == RESEARCH_OS_VERSION == CURRENT_RELEASE.version
    assert RESEARCH_OS_VERSION == "1.6.01"
    assert CORE_API_VERSION == CURRENT_RELEASE.core_api_version == "2.0"

    version_source = Path("src/research_os/version.py").read_text(encoding="utf-8")
    tree = ast.parse(version_source)
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert imports == []

    metadata = json.loads(Path("research_os_version.json").read_text(encoding="utf-8"))
    assert metadata == CURRENT_RELEASE.to_public_metadata()

    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert "version" not in project["project"]
    assert project["project"]["dynamic"] == ["version"]
    assert project["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "research_os.version.RESEARCH_OS_VERSION"
    }


def test_release_gate_derives_required_checks_from_manifest_packs():
    resolved = resolve_release_checks(CURRENT_RELEASE)
    assert tuple(resolved) == REQUIRED
    assert CURRENT_RELEASE.verification_packs == (
        "m1-core-runtime",
        "m2-persistence-http",
        "m3-professional-foundations",
        "m4-reporting-replay",
        "m5-quality-release",
        "v1-6-01-professional-closure",
        "release-governance",
    )
    assert resolved["snapshot_schema_v2"] == "tests/unit/snapshots"
    assert resolved["snapshot_canonicalization_v2"] == "tests/property/snapshots"
    assert resolved["sql_persistence_v2"] == "tests/integration/storage"
    assert resolved["runtime_snapshot_transaction_v2"] == (
        "tests/integration/runtime/test_run_snapshot_transaction.py"
    )
    assert resolved["http_api_v1_unit"] == "tests/unit/api"
    assert resolved["http_api_v1_integration"] == "tests/integration/api"
    assert resolved["http_api_v1_contract"] == "tests/contract/api"
    assert resolved["m3_metrics"] == "tests/unit/metrics"
    assert resolved["m3_forecasting"] == "tests/unit/forecasting"
    assert resolved["current_reporting_v2"] == (
        "tests/unit/reporting/test_v1_6_current_reporting.py"
    )
    assert resolved["historical_replay_v2"] == ("tests/unit/release/test_historical_replay_v1_6.py")
    assert resolved["presentation_pipeline_v2"] == (
        "tests/integration/presentation/test_v1_6_pipeline.py"
    )
    assert resolved["clean_break_v2"] == ("tests/regression/architecture/test_clean_break_v1_6.py")
    assert resolved["m5_dependency_rules"] == (
        "tests/regression/architecture/test_dependency_rules_v1_6.py"
    )
    assert resolved["m5_release_contract"] == (
        "tests/regression/architecture/test_release_contract_v1_6_0.py"
    )
    assert resolved["v1_6_01_professional_wiring"] == (
        "tests/regression/professional/test_v1_6_01_professional_wiring.py"
    )
    assert resolved["v1_6_01_investor_body"] == (
        "tests/regression/presentation/test_v1_6_01_investor_body.py"
    )
    assert resolved["v1_6_01_field_acceptance_contract"] == (
        "tests/integration/presentation/test_field_acceptance_v1_6_01.py"
    )
    assert resolved["release_governance"] == (
        "tests/regression/architecture/test_release_governance.py"
    )
    for nodeid in resolved.values():
        assert Path(nodeid.split("::", 1)[0]).exists(), nodeid


def test_release_runtime_has_no_patch_version_specific_module():
    assert list(Path("src/research_os/release").glob("runtime_v*.py")) == []
    source = Path("scripts/verify_release_pipeline.py").read_text(encoding="utf-8")
    assert "from research_os.release.manifest import CURRENT_RELEASE" in source
    assert "from research_os.release.verification import resolve_release_checks" in source
    assert "resolve_release_checks(CURRENT_RELEASE)" in source
    assert "runtime_v" not in source
    assert "release_gate_v1_" not in source


def test_field_replay_profiles_are_unique_and_historical_profiles_are_frozen():
    profiles = resolve_replay_profiles(CURRENT_RELEASE)
    ids = [profile.profile_id for profile in profiles]
    assert len(ids) == len(set(ids))
    assert ids == list(CURRENT_RELEASE.field_replay_profiles)
    assert ids == [
        "field-v1.5.08",
        "field-v1.5.09",
        "field-v1.5.10",
        "field-v1.5.11",
        "field-v1.5.12",
    ]

    for profile in profiles:
        assert profile.frozen is True
        assert REPLAY_REGISTRY[profile.profile_id] == profile
        assert len(profile.source_commit_sha) == 40
        assert profile.expected_core_api_version == "1.0"

    assert CURRENT_RELEASE.status == "stable"


def test_ci_uses_stable_release_pipeline_instead_of_patch_specific_blocks():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python scripts/verify_release_pipeline.py" in workflow
    for version in ("1_5_08", "1_5_09", "1_5_10", "1_5_11", "1_5_12"):
        assert f"render_field_acceptance_v{version}.py" not in workflow
    assert "build/field-acceptance-*" in workflow
    assert "build/historical-replay" in workflow
    assert "fetch-depth: 0" in workflow


def test_v1_6_0_delivery_bundle_is_frozen_to_the_final_release_commit():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    release_sha = "1cb163b38ac971dfc045e6adfe31e67efdd87af7"
    guard = (
        "github.event_name == 'push' && github.ref == 'refs/heads/main' && "
        f"github.sha == '{release_sha}'"
    )
    assert workflow.count(f"if: {guard}") == 2


def test_release_governance_keeps_acceptance_company_identity_out_of_production():
    forbidden = ("300034", "001287", "301073", "钢研高纳", "中电港", "君亭酒店")
    offenders: list[tuple[str, str]] = []
    for path in Path("src/research_os").rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for value in forbidden:
            if value in content:
                offenders.append((str(path), value))
    assert offenders == []
