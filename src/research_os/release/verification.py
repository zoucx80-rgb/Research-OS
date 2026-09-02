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

CHECK_REGISTRY: Mapping[str, str] = {
    **_BASELINE_CHECKS,
    **_RELEASE_GOVERNANCE_CHECKS,
}

PACK_REGISTRY: Mapping[str, VerificationPack] = {
    "m1-core-runtime": VerificationPack(
        pack_id="m1-core-runtime",
        check_ids=tuple(_BASELINE_CHECKS),
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
