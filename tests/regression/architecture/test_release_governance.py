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
    assert CORE_API_VERSION == CURRENT_RELEASE.core_api_version

    version_source = Path("src/research_os/version.py").read_text(encoding="utf-8")
    tree = ast.parse(version_source)
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
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
        "release-governance",
    )
    assert resolved["release_governance"] == (
        "tests/regression/architecture/test_release_governance.py"
    )
    for nodeid in resolved.values():
        assert Path(nodeid.split("::", 1)[0]).exists(), nodeid


def test_release_runtime_has_no_patch_version_specific_module():
    assert list(Path("src/research_os/release").glob("runtime_v*.py")) == []
    source = Path("scripts/release_gate_v1_1.py").read_text(encoding="utf-8")
    assert "research_os.release.runtime import run_release_checks" in source
    assert "runtime_v" not in source


def test_field_replay_profiles_are_unique_and_historical_profiles_are_frozen():
    profiles = resolve_replay_profiles(CURRENT_RELEASE)
    ids = [profile.profile_id for profile in profiles]
    assert len(ids) == len(set(ids))
    assert ids == list(CURRENT_RELEASE.field_replay_profiles)
    assert profiles == ()

    for profile_id in ("field-v1.5.08", "field-v1.5.09", "field-v1.5.10", "field-v1.5.11"):
        assert REPLAY_REGISTRY[profile_id].frozen is True
    assert REPLAY_REGISTRY["field-v1.5.12"].frozen is False

    assert CURRENT_RELEASE.status == "development"


def test_ci_uses_stable_release_pipeline_instead_of_patch_specific_blocks():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python scripts/verify_release_pipeline.py" in workflow
    for version in ("1_5_08", "1_5_09", "1_5_10", "1_5_11"):
        assert f"render_field_acceptance_v{version}.py" not in workflow
    assert "build/field-acceptance-*" in workflow


def test_release_governance_keeps_acceptance_company_identity_out_of_production():
    forbidden = ("300034", "001287", "301073", "钢研高纳", "中电港", "君亭酒店")
    offenders: list[tuple[str, str]] = []
    for path in Path("src/research_os").rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for value in forbidden:
            if value in content:
                offenders.append((str(path), value))
    assert offenders == []
