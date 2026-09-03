from __future__ import annotations

import json
from pathlib import Path
import tomllib

from research_os.release.manifest import CURRENT_RELEASE
from research_os.release.verification import resolve_release_checks


EXPECTED_PACKS = (
    "m1-core-runtime",
    "m2-persistence-http",
    "m3-professional-foundations",
    "m4-reporting-replay",
    "m5-quality-release",
    "release-governance",
)


def test_v1_6_0_release_is_stable_and_manifest_selected_gates_cover_all_milestones() -> None:
    assert CURRENT_RELEASE.status == "stable"
    assert CURRENT_RELEASE.verification_packs == EXPECTED_PACKS

    resolved = resolve_release_checks(CURRENT_RELEASE)
    required = {
        "m3_financial_values",
        "m3_metrics",
        "m3_policies",
        "m3_router",
        "m3_thesis_decision",
        "m3_valuation",
        "m3_forecasting",
        "m3_peers",
        "m3_monitoring",
        "m5_dependency_rules",
        "m5_release_contract",
        "m5_installed_distribution",
    }
    assert required <= set(resolved)


def test_public_metadata_is_stable_manifest_projection() -> None:
    metadata = json.loads(Path("research_os_version.json").read_text(encoding="utf-8"))
    assert metadata == CURRENT_RELEASE.to_public_metadata()
    assert metadata["status"] == "stable"


def test_release_tooling_dependencies_are_declared() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    test_dependencies = set(project["project"]["optional-dependencies"]["test"])
    required_prefixes = (
        "ruff",
        "import-linter",
        "pip-audit",
        "build",
        "twine",
        "pytest-cov",
    )
    for prefix in required_prefixes:
        assert any(dep.startswith(prefix) for dep in test_dependencies), prefix


def test_ci_is_split_into_m5_quality_release_jobs() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    for job in (
        "quality:",
        "unit:",
        "integration:",
        "acceptance:",
        "security-package:",
        "release-gate:",
    ):
        assert job in workflow
    assert "fetch-depth: 0" in workflow
    assert "python -m playwright install --with-deps chromium" in workflow
    assert "python scripts/verify_distribution.py" in workflow


def test_release_docs_reflect_m5_only_single_commit_delivery() -> None:
    adr = Path(
        "docs/architecture/adr-0002-v1-6-0-controlled-breaking-contract-upgrade.md"
    ).read_text(encoding="utf-8")
    assert "**状态：** Accepted" in adr

    readme = Path("README.md").read_text(encoding="utf-8")
    assert "docs/architecture/adr-0002-v1-6-0-controlled-breaking-contract-upgrade.md" in readme
    assert "docs/adr/adr-0002-v1-6-0-controlled-breaking-contract-upgrade.md" not in readme

    m5 = Path(
        "docs/superpowers/plans/2026-08-31-research-os-v1-6-0-m5-quality-release-delivery.md"
    ).read_text(encoding="utf-8")
    assert "abd19bbc7e22d7958df853333e0ba8cedff39f6f" in m5
    assert "M1–M4" in m5
    assert "M5" in m5
    assert "ahead 1" in m5
