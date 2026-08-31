from __future__ import annotations

from datetime import datetime, timezone

from research_os.domain.evidence import Evidence
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.runtime.financial_snapshot import (
    FinancialFactSnapshotModule,
    build_financial_fact_snapshot,
)
from research_os.runtime.state import ResearchStateView


DECISION_TS = datetime(2026, 8, 30, tzinfo=timezone.utc)


def _context() -> ResearchContext:
    company_id = "synthetic:depth"
    evidence = [
        Evidence(
            evidence_id="ev:revenue",
            company_id=company_id,
            evidence_type="filing_fact",
            period_end="2026-06-30",
            period="2026H1",
            publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
            ingested_at=DECISION_TS,
            value=2_053_495_665.67,
            unit="元",
            source_table="revenue",
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
        ),
        Evidence(
            evidence_id="ev:margin-change",
            company_id=company_id,
            evidence_type="calculated_metric",
            period_end="2026-06-30",
            period="2026H1",
            publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
            ingested_at=DECISION_TS,
            value=-0.0266,
            unit="ratio",
            source_table="margin_change",
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
            formula_version="h1-yoy-margin-change@1",
        ),
        Evidence(
            evidence_id="ev:unsupported",
            company_id=company_id,
            evidence_type="filing_fact",
            period_end="2026-06-30",
            period="2026H1",
            publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
            ingested_at=DECISION_TS,
            value="do not expose generically",
            unit=None,
            source_table="arbitrary_note",
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
        ),
    ]
    facts = {
        "revenue": 2_053_495_665.67,
        "margin_change": -0.0266,
        "period_type": "H1",
        "arbitrary_note": "do not expose generically",
    }
    evidence_by_fact = {
        "revenue": ["ev:revenue"],
        "margin_change": ["ev:margin-change"],
        "arbitrary_note": ["ev:unsupported"],
    }
    return ResearchContext(
        run_id="run:depth",
        company=CompanyRef(company_id=company_id),
        decision_ts=DECISION_TS,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1" * 40,
            research_os_version="1.5.9",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(values=facts, evidence_by_fact=evidence_by_fact),
        options=ResearchOptions(),
    )


def test_snapshot_copies_supported_pit_facts_with_lineage_without_deriving_missing_values():
    context = _context()

    snapshot = build_financial_fact_snapshot(context)

    by_key = {item.fact_key: item for item in snapshot.facts}
    assert set(by_key) == {"revenue", "margin_change"}
    assert by_key["revenue"].value == 2_053_495_665.67
    assert by_key["revenue"].unit == "元"
    assert by_key["revenue"].period == "2026H1"
    assert by_key["revenue"].evidence_ids == ["ev:revenue"]
    assert by_key["margin_change"].formula_version == "h1-yoy-margin-change@1"
    assert "revenue_growth" not in by_key
    assert "arbitrary_note" not in by_key


def test_snapshot_module_requires_pit_and_provides_canonical_artifact():
    context = _context()
    module = FinancialFactSnapshotModule()

    assert module.spec.requires == frozenset({"evidence.pit"})
    assert module.spec.provides == frozenset({"financial.fact_snapshot"})

    empty = module.run(context, ResearchStateView({"evidence.pit": []}))
    assert empty.status == "INSUFFICIENT_EVIDENCE"
    assert empty.artifacts["financial.fact_snapshot"].facts == []

    result = module.run(
        context,
        ResearchStateView({"evidence.pit": context.evidence.as_of(DECISION_TS)}),
    )
    assert result.status == "PASS"
    assert [item.fact_key for item in result.artifacts["financial.fact_snapshot"].facts] == [
        "revenue",
        "margin_change",
    ]
    assert result.evidence_ids == ["ev:revenue", "ev:margin-change"]
