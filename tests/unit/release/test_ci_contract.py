from pathlib import Path

from research_os.release.manifest import CURRENT_RELEASE
from research_os.release.verification import resolve_release_checks


def test_current_release_resolves_nonempty_unique_verification_checks():
    checks = resolve_release_checks(CURRENT_RELEASE)
    assert checks
    assert len(checks) == len(set(checks))
    assert "m1-core-runtime" in CURRENT_RELEASE.verification_packs
    assert "m2-persistence-http" in CURRENT_RELEASE.verification_packs
    assert "m4-reporting-replay" in CURRENT_RELEASE.verification_packs
    assert "release-governance" in CURRENT_RELEASE.verification_packs


def test_ci_delegates_to_canonical_pipeline_with_full_history():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "fetch-depth: 0" in workflow
    assert "python scripts/verify_release_pipeline.py" in workflow


def test_pipeline_orders_current_checks_replay_full_suite_and_mypy():
    pipeline = Path("scripts/verify_release_pipeline.py").read_text(encoding="utf-8")
    main_source = pipeline.split("def main() -> None:", 1)[1]
    release_checks = main_source.index("status = _run_release_checks()")
    current_acceptance = main_source.index("_run_current_field_acceptance()")
    historical_replay = main_source.index("_run_field_replays()")
    full_suite = main_source.index('"full pytest suite"')
    mypy = main_source.index('"mypy"')
    assert release_checks < current_acceptance < historical_replay < full_suite < mypy
