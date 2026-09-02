from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from research_os.contracts.evidence import (
    EvidenceRef,
    EvidenceSet,
    evidence_content_fingerprint,
)
from research_os.domain.evidence import Evidence
from research_os.runtime.context import EvidenceView


def _evidence() -> Evidence:
    timestamp = datetime(2026, 8, 20, tzinfo=timezone.utc)
    return Evidence(
        evidence_id="ev:revenue",
        revision_no=1,
        company_id="synthetic:company",
        evidence_type="filing_fact",
        publish_ts=timestamp,
        ingested_at=timestamp,
        value=100,
        unit="CNY",
        period="2026H1",
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
    )


def test_evidence_ref_requires_a_revision_and_sha256_fingerprint():
    with pytest.raises(ValidationError):
        EvidenceRef(evidence_id="ev:revenue", revision=0, content_fingerprint="0" * 64)
    with pytest.raises(ValidationError):
        EvidenceRef(evidence_id="ev:revenue", revision=1, content_fingerprint="not-a-hash")


def test_evidence_set_binds_every_row_to_its_exact_revision_and_content():
    evidence = _evidence()
    reference = EvidenceRef(
        evidence_id=evidence.evidence_id,
        revision=evidence.revision_no,
        content_fingerprint=evidence_content_fingerprint(evidence),
    )

    assert EvidenceSet(items=(evidence,), evidence_refs=(reference,)).items == (
        evidence,
    )
    with pytest.raises(ValidationError, match="bound to its revision"):
        EvidenceSet(
            items=(evidence,),
            evidence_refs=(reference.model_copy(update={"revision": 2}),),
        )


def test_bound_view_rejects_revision_or_content_fingerprint_mismatch():
    evidence = _evidence()
    view = EvidenceView(
        [evidence],
        company_id=evidence.company_id,
        decision_ts=evidence.publish_ts,
    )
    valid = EvidenceRef(
        evidence_id=evidence.evidence_id,
        revision=evidence.revision_no,
        content_fingerprint=evidence_content_fingerprint(evidence),
    )

    assert view.get(valid) == evidence
    assert view.get(valid.model_copy(update={"revision": 2})) is None
    assert view.get(valid.model_copy(update={"content_fingerprint": "0" * 64})) is None


def test_evidence_fingerprint_normalizes_equivalent_timezone_offsets():
    utc = _evidence()
    same_in_shanghai = utc.model_copy(
        update={
            "publish_ts": utc.publish_ts.astimezone(timezone(timedelta(hours=8))),
            "ingested_at": utc.ingested_at.astimezone(timezone(timedelta(hours=8))),
        }
    )

    assert evidence_content_fingerprint(utc) == evidence_content_fingerprint(
        same_in_shanghai
    )


def test_evidence_fingerprint_normalizes_nested_datetime_values():
    utc = _evidence().model_copy(
        update={
            "value": {
                "observed_at": datetime(2026, 8, 20, 8, tzinfo=timezone.utc),
                "history": (
                    datetime(2026, 8, 19, 16, tzinfo=timezone.utc),
                ),
            },
        }
    )
    same_instants = utc.model_copy(
        update={
            "value": {
                "observed_at": datetime(
                    2026,
                    8,
                    20,
                    16,
                    tzinfo=timezone(timedelta(hours=8)),
                ),
                "history": (
                    datetime(
                        2026,
                        8,
                        20,
                        tzinfo=timezone(timedelta(hours=8)),
                    ),
                ),
            },
        }
    )

    assert evidence_content_fingerprint(utc) == evidence_content_fingerprint(
        same_instants
    )


def test_evidence_fingerprint_rejects_naive_nested_datetime_values():
    evidence = _evidence().model_copy(
        update={"normalized_value": {"observed_at": datetime(2026, 8, 20, 8)}}
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        evidence_content_fingerprint(evidence)


def test_evidence_fingerprint_type_tags_cannot_collide_with_mapping_content():
    timestamp = datetime(2026, 8, 20, 8, tzinfo=timezone.utc)
    typed = _evidence().model_copy(update={"value": timestamp})
    mapping = _evidence().model_copy(
        update={
            "value": {
                "$datetime": "2026-08-20T08:00:00.000000Z",
            }
        }
    )

    assert evidence_content_fingerprint(typed) != evidence_content_fingerprint(mapping)
