from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .baseline import CHECKS as _BASELINE_CHECKS
from .manifest import ReleaseManifest


@dataclass(frozen=True)
class VerificationPack:
    pack_id: str
    check_ids: tuple[str, ...]


_RELEASE_GOVERNANCE_CHECKS: dict[str, str] = {
    "release_governance": "tests/regression/architecture/test_release_governance.py",
}
_M2_PERSISTENCE_HTTP_CHECKS: dict[str, str] = {
    "snapshot_schema_v2": "tests/unit/snapshots",
    "snapshot_canonicalization_v2": "tests/property/snapshots",
    "sql_persistence_v2": "tests/integration/storage",
    "runtime_snapshot_transaction_v2": (
        "tests/integration/runtime/test_run_snapshot_transaction.py"
    ),
    "http_api_v1_unit": "tests/unit/api",
    "http_api_v1_integration": "tests/integration/api",
    "http_api_v1_contract": "tests/contract/api",
}
_M4_REPORTING_REPLAY_CHECKS: dict[str, str] = {
    "current_reporting_v2": "tests/unit/reporting/test_v1_6_current_reporting.py",
    "historical_replay_v2": "tests/unit/release/test_historical_replay_v1_6.py",
    "presentation_pipeline_v2": "tests/integration/presentation/test_v1_6_pipeline.py",
    "field_acceptance_contract_v2": (
        "tests/integration/presentation/test_field_acceptance_v1_6_0.py"
    ),
    "clean_break_v2": "tests/regression/architecture/test_clean_break_v1_6.py",
    "v1_6_examples": "tests/integration/examples/test_v1_6_examples.py",
}

CHECK_REGISTRY: Mapping[str, str] = {
    **_BASELINE_CHECKS,
    **_M2_PERSISTENCE_HTTP_CHECKS,
    **_M4_REPORTING_REPLAY_CHECKS,
    **_RELEASE_GOVERNANCE_CHECKS,
}

PACK_REGISTRY: Mapping[str, VerificationPack] = {
    "m1-core-runtime": VerificationPack(
        pack_id="m1-core-runtime",
        check_ids=tuple(_BASELINE_CHECKS),
    ),
    "m2-persistence-http": VerificationPack(
        pack_id="m2-persistence-http",
        check_ids=tuple(_M2_PERSISTENCE_HTTP_CHECKS),
    ),
    "m4-reporting-replay": VerificationPack(
        pack_id="m4-reporting-replay",
        check_ids=tuple(_M4_REPORTING_REPLAY_CHECKS),
    ),
    "release-governance": VerificationPack(
        pack_id="release-governance",
        check_ids=tuple(_RELEASE_GOVERNANCE_CHECKS),
    ),
}


def resolve_release_checks(manifest: ReleaseManifest) -> dict[str, str]:
    """Resolve manifest-selected packs into one ordered, fail-closed check map."""

    resolved: dict[str, str] = {}
    for pack_id in manifest.verification_packs:
        try:
            pack = PACK_REGISTRY[pack_id]
        except KeyError as exc:
            raise ValueError(f"unknown verification pack: {pack_id}") from exc
        for check_id in pack.check_ids:
            if check_id in resolved:
                raise ValueError(f"duplicate verification check: {check_id}")
            try:
                resolved[check_id] = CHECK_REGISTRY[check_id]
            except KeyError as exc:
                raise ValueError(
                    f"verification pack {pack_id!r} references unknown check {check_id!r}"
                ) from exc
    if not resolved:
        raise ValueError("release must select at least one verification check")
    return resolved
