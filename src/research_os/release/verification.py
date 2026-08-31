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

_SEMANTIC_CORRECTNESS_CHECKS: dict[str, str] = {
    "semantic_signal_contract_v1_5_11": "tests/unit/thesis/test_semantic_signals_v1_5_11.py",
    "thesis_lifecycle_v1_5_11": "tests/unit/thesis/test_lifecycle_semantics_v1_5_11.py",
    "expectation_missingness_v1_5_11": "tests/unit/decision/test_missing_expectation_v1_5_11.py",
    "semantic_runtime_v1_5_11": "tests/integration/runtime/test_semantic_thesis_runtime_v1_5_11.py",
    "presentation_integrity_v1_5_11": "tests/unit/reporting/test_semantic_integrity_v1_5_11.py",
    "semantic_output_patterns_v1_5_11": "tests/regression/research_patterns/test_v1_5_11_semantic_output_patterns.py",
    "semantic_correctness_patterns_v1_5_11": "tests/regression/research_patterns/test_v1_5_11_semantic_correctness.py",
    "semantic_architecture_v1_5_11": "tests/regression/architecture/test_semantic_correctness_contract_v1_5_11.py",
    "semantic_field_v1_5_11": "tests/integration/presentation/test_field_acceptance_v1_5_11.py",
    "release_contract_v1_5_11": "tests/regression/architecture/test_release_contract_v1_5_11.py",
}

_SEMANTIC_PRESERVATION_CHECKS: dict[str, str] = {
    "claim_strength_contract_v1_5_12": "tests/unit/semantics/test_claims.py",
    "semantic_context_contract_v1_5_12": "tests/unit/completeness/test_semantic_context_v1_5_12.py",
    "semantic_preservation_runtime_v1_5_12": "tests/integration/runtime/test_semantic_preservation_v1_5_12.py",
    "valuation_reconciliation_v1_5_12": "tests/unit/valuation/test_reconciliation_v1_5_12.py",
    "valuation_reconciliation_runtime_v1_5_12": "tests/integration/runtime/test_valuation_reconciliation_v1_5_12.py",
    "semantic_preservation_reporting_v1_5_12": "tests/unit/reporting/test_semantic_preservation_v1_5_12.py",
    "semantic_preservation_architecture_v1_5_12": "tests/regression/architecture/test_semantic_preservation_contract_v1_5_12.py",
    "semantic_preservation_field_v1_5_12": "tests/integration/presentation/test_field_acceptance_v1_5_12.py",
    "release_contract_v1_5_12": "tests/regression/architecture/test_release_contract_v1_5_12.py",
}

CHECK_REGISTRY: Mapping[str, str] = {
    **_BASELINE_CHECKS,
    **_RELEASE_GOVERNANCE_CHECKS,
    **_SEMANTIC_CORRECTNESS_CHECKS,
    **_SEMANTIC_PRESERVATION_CHECKS,
}

PACK_REGISTRY: Mapping[str, VerificationPack] = {
    "stable-baseline": VerificationPack(
        pack_id="stable-baseline",
        check_ids=tuple(_BASELINE_CHECKS),
    ),
    "release-governance": VerificationPack(
        pack_id="release-governance",
        check_ids=tuple(_RELEASE_GOVERNANCE_CHECKS),
    ),
    "semantic-correctness": VerificationPack(
        pack_id="semantic-correctness",
        check_ids=tuple(_SEMANTIC_CORRECTNESS_CHECKS),
    ),
    "semantic-preservation": VerificationPack(
        pack_id="semantic-preservation",
        check_ids=tuple(_SEMANTIC_PRESERVATION_CHECKS),
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
