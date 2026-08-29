from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.version import CORE_API_VERSION


def _evidence(evidence_id: str, publish_ts: datetime) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        company_id="synthetic:1",
        evidence_type=EvidenceType.FILING_FACT,
        publish_ts=publish_ts,
        ingested_at=publish_ts,
        value=100.0,
        confidence_grade=ConfidenceGrade.A,
        verification_status=VerificationStatus.PRIMARY_VERIFIED,
    )


def test_legacy_fact_view_preserves_missing_and_returns_copied_lineage():
    view = LegacyFactView(
        values={"revenue": 100.0, "ocf": None},
        evidence_by_fact={"revenue": ["ev:revenue"]},
    )

    assert view.get("revenue") == 100.0
    assert view.get("ocf") is None
    assert view.get("missing") is None
    assert view.as_mapping()["ocf"] is None

    ids = view.evidence_ids("revenue")
    ids.append("mutated")
    assert view.evidence_ids("revenue") == ["ev:revenue"]


def test_legacy_evidence_view_filters_point_in_time_and_resolves_by_id():
    decision_ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
    before = _evidence("ev:before", decision_ts - timedelta(days=1))
    after = _evidence("ev:after", decision_ts + timedelta(days=1))
    view = LegacyEvidenceView([after, before])

    assert [item.evidence_id for item in view.as_of(decision_ts)] == ["ev:before"]
    assert view.get("ev:after") == after
    assert view.get("missing") is None


def test_context_carries_frozen_baseline_and_core_api_version():
    baseline = BaselineFingerprint(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        commit_sha="a" * 40,
        research_os_version="1.3.0",
        core_api_version=CORE_API_VERSION,
    )
    context = ResearchContext(
        run_id="run:1",
        company=CompanyRef(company_id="synthetic:1"),
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        baseline=baseline,
        evidence=LegacyEvidenceView([]),
        facts=LegacyFactView(values={}, evidence_by_fact={}),
        options=ResearchOptions(),
    )

    assert context.baseline.core_api_version == "1.0"
    with pytest.raises(ValidationError):
        context.company.company_id = "mutated"
