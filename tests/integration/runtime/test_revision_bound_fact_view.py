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
from research_os.period.models import ReportingPeriod
from research_os.contracts.values import AccountingScope
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.runtime.financial_snapshot import (
    FinancialFactSnapshotModule,
    build_financial_fact_snapshot,
)
from research_os.runtime.core_artifacts import EVIDENCE_PIT, build_core_artifact_catalog
from research_os.contracts.artifacts import ArtifactStore, ArtifactWrite
from research_os.runtime.state import ResearchStateView


DECISION_TS = datetime(2026, 8, 29, tzinfo=timezone.utc)
COMPANY_ID = "synthetic:revision-bound"


def _evidence(*, revision: int, publish_ts: datetime, value: int, company_id: str = COMPANY_ID):
    return Evidence(
        evidence_id="ev:revenue",
        revision_no=revision,
        company_id=company_id,
        evidence_type="filing_fact",
        publish_ts=publish_ts,
        ingested_at=publish_ts,
        value=value,
        unit="CNY",
        period="2026H1",
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
    )


def _baseline() -> BaselineFingerprint:
    return BaselineFingerprint(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        commit_sha="d37e360cea3cd32f18cacc634ab7e5dec967c4db",
        research_os_version="1.6.0",
        core_api_version="2.0",
    )


def _context(evidence: list[Evidence], *, references: tuple[EvidenceRef, ...] | None = None):
    view = EvidenceView(evidence, company_id=COMPANY_ID, decision_ts=DECISION_TS)
    facts = FactView(
        company_id=COMPANY_ID,
        decision_ts=DECISION_TS,
        values={"revenue": 100},
        evidence_refs_by_fact={"revenue": references if references is not None else view.refs()},
        reporting_period=ReportingPeriod(period_type="H1"),
        accounting_scope=AccountingScope(),
    )
    return ResearchContext(
        run_id="run:revision-bound",
        company=CompanyRef(company_id=COMPANY_ID),
        decision_ts=DECISION_TS,
        baseline=_baseline(),
        evidence=view,
        facts=facts,
    )


def test_future_revision_cannot_support_a_historical_fact():
    revision_1 = _evidence(revision=1, publish_ts=DECISION_TS - timedelta(days=9), value=100)
    revision_2 = _evidence(revision=2, publish_ts=DECISION_TS + timedelta(days=2), value=999)
    context = _context([revision_1, revision_2])

    snapshot = build_financial_fact_snapshot(context)

    assert [(item.fact_key, item.value) for item in snapshot.facts] == [("revenue", 100)]
    assert [(ref.evidence_id, ref.revision) for ref in context.evidence.refs()] == [("ev:revenue", 1)]
    assert context.facts.evidence_refs("revenue") == context.evidence.refs()


def test_evidence_view_is_order_independent_and_rejects_raw_ids_and_bad_fingerprints():
    revision_1 = _evidence(revision=1, publish_ts=DECISION_TS - timedelta(days=9), value=100)
    revision_2 = _evidence(revision=2, publish_ts=DECISION_TS + timedelta(days=2), value=999)

    forward = EvidenceView([revision_1, revision_2], company_id=COMPANY_ID, decision_ts=DECISION_TS)
    reverse = EvidenceView([revision_2, revision_1], company_id=COMPANY_ID, decision_ts=DECISION_TS)
    reference = forward.refs()[0]
    wrong_fingerprint = reference.model_copy(update={"content_fingerprint": "0" * 64})

    assert forward.refs() == reverse.refs()
    assert forward.get(reference) == reverse.get(reference) == revision_1
    assert forward.get(wrong_fingerprint) is None
    with pytest.raises(TypeError, match="EvidenceRef"):
        forward.get("ev:revenue")  # type: ignore[arg-type]


def test_evidence_view_rejects_cross_company_rows_and_conflicting_same_revision_content():
    foreign = _evidence(revision=1, publish_ts=DECISION_TS, value=100, company_id="synthetic:other-company")
    first = _evidence(revision=1, publish_ts=DECISION_TS, value=100)
    conflicting = _evidence(revision=1, publish_ts=DECISION_TS, value=999)

    with pytest.raises(ValueError, match="cross-company evidence"):
        EvidenceView([foreign], company_id=COMPANY_ID, decision_ts=DECISION_TS)
    for rows in ((first, conflicting), (conflicting, first)):
        with pytest.raises(ValueError, match="conflicting evidence revision"):
            EvidenceView(rows, company_id=COMPANY_ID, decision_ts=DECISION_TS)


def test_conflicting_future_records_do_not_affect_the_historical_view():
    historical = _evidence(
        revision=1,
        publish_ts=DECISION_TS - timedelta(days=1),
        value=100,
    )
    future_first = _evidence(
        revision=2,
        publish_ts=DECISION_TS + timedelta(days=1),
        value=999,
    )
    future_conflict = _evidence(
        revision=2,
        publish_ts=DECISION_TS + timedelta(days=1),
        value=888,
    )

    view = EvidenceView(
        [historical, future_first, future_conflict],
        company_id=COMPANY_ID,
        decision_ts=DECISION_TS,
    )

    assert view.get(view.refs()[0]) == historical


def test_evidence_view_includes_cutoff_and_copies_input_against_repository_mutation():
    source = [_evidence(revision=1, publish_ts=DECISION_TS, value=100)]
    view = EvidenceView(source, company_id=COMPANY_ID, decision_ts=DECISION_TS)
    source.append(_evidence(revision=2, publish_ts=DECISION_TS - timedelta(days=1), value=999))

    assert view.get(view.refs()[0]).revision_no == 1
    assert view.get(view.refs()[0]).publish_ts == DECISION_TS


def test_evidence_view_constructs_from_a_company_and_cutoff_bound_source():
    before = _evidence(revision=1, publish_ts=DECISION_TS - timedelta(days=1), value=100)
    after = _evidence(revision=2, publish_ts=DECISION_TS + timedelta(days=1), value=999)

    class Source:
        def as_of(self, company_id: str, decision_ts: datetime) -> list[Evidence]:
            assert company_id == COMPANY_ID
            assert decision_ts == DECISION_TS
            return [before, after]

    view = EvidenceView(Source(), company_id=COMPANY_ID, decision_ts=DECISION_TS)

    assert view.get(view.refs()[0]) == before


def test_financial_snapshot_preserves_revision_lineage_for_normalized_facts():
    evidence = _evidence(revision=1, publish_ts=DECISION_TS, value=999).model_copy(
        update={"value": "CNY 100", "normalized_value": 100}
    )
    context = _context([evidence])

    snapshot = build_financial_fact_snapshot(context)
    assert snapshot.facts[0].evidence_refs == context.evidence.refs()

    catalog = build_core_artifact_catalog()
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            key=EVIDENCE_PIT,
            value=EvidenceSet(
                items=(evidence,),
                evidence_refs=context.evidence.refs(),
            ),
            producer_id="core:pit-lineage",
            evidence_refs=context.evidence.refs(),
        )
    )
    result = FinancialFactSnapshotModule().run(
        context,
        ResearchStateView(store.freeze()),
    )

    assert result.status == "PASS"
    assert result.writes[0].evidence_refs == context.evidence.refs()


def test_fact_view_rejects_raw_evidence_ids_and_copies_values_and_lineage():
    evidence = _evidence(revision=1, publish_ts=DECISION_TS, value=100)
    reference = EvidenceRef(
        evidence_id=evidence.evidence_id,
        revision=evidence.revision_no,
        content_fingerprint=evidence_content_fingerprint(evidence),
    )
    values = {"revenue": {"value": 100}}
    references = {"revenue": (reference,)}
    view = FactView(
        company_id=COMPANY_ID,
        decision_ts=DECISION_TS,
        values=values,
        evidence_refs_by_fact=references,
        reporting_period=ReportingPeriod(period_type="FY"),
        accounting_scope=AccountingScope(),
    )
    values["revenue"]["value"] = 999
    references["revenue"] = ()

    assert view.get("revenue") == {"value": 100}
    assert view.evidence_refs("revenue") == (reference,)
    assert view.reporting_period == ReportingPeriod(period_type="FY")
    assert view.accounting_scope == AccountingScope()
    assert not hasattr(view, "evidence_ids")
    with pytest.raises(TypeError, match="EvidenceRef"):
        FactView(
            company_id=COMPANY_ID,
            decision_ts=DECISION_TS,
            values={"revenue": 100},
            evidence_refs_by_fact={"revenue": ("ev:revenue",)},  # type: ignore[arg-type]
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        )


def test_fact_view_rejects_any_value_without_revision_bound_lineage():
    with pytest.raises(ValueError, match="missing evidence references.*revenue"):
        FactView(
            company_id=COMPANY_ID,
            decision_ts=DECISION_TS,
            values={"revenue": 100},
            evidence_refs_by_fact={},
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        )


def test_fact_view_requires_explicit_period_and_accounting_scope():
    with pytest.raises(TypeError):
        FactView(
            company_id=COMPANY_ID,
            decision_ts=DECISION_TS,
            values={},
            evidence_refs_by_fact={},
        )


def test_fact_view_canonicalizes_lineage_and_rejects_conflicting_revisions():
    later_id = EvidenceRef(
        evidence_id="ev:zeta",
        revision=1,
        content_fingerprint="1" * 64,
    )
    earlier_id = EvidenceRef(
        evidence_id="ev:alpha",
        revision=1,
        content_fingerprint="2" * 64,
    )
    view = FactView(
        company_id=COMPANY_ID,
        decision_ts=DECISION_TS,
        values={"revenue": 100},
        evidence_refs_by_fact={"revenue": (later_id, earlier_id, later_id)},
        reporting_period=ReportingPeriod(period_type="FY"),
        accounting_scope=AccountingScope(),
    )

    assert view.evidence_refs("revenue") == (earlier_id, later_id)

    with pytest.raises(ValueError, match="conflicting revisions.*ev:alpha"):
        FactView(
            company_id=COMPANY_ID,
            decision_ts=DECISION_TS,
            values={"revenue": 100},
            evidence_refs_by_fact={
                "revenue": (
                    earlier_id,
                    earlier_id.model_copy(update={"revision": 2}),
                )
            },
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        )


def test_research_context_requires_prebound_views_with_matching_identity_and_resolved_refs():
    evidence = _evidence(revision=1, publish_ts=DECISION_TS, value=100)
    view = EvidenceView([evidence], company_id=COMPANY_ID, decision_ts=DECISION_TS)
    other_company_facts = FactView(
        company_id="synthetic:other-company",
        decision_ts=DECISION_TS,
        values={},
        evidence_refs_by_fact={},
        reporting_period=ReportingPeriod(period_type="FY"),
        accounting_scope=AccountingScope(),
    )
    unresolved = EvidenceRef(evidence_id="ev:missing", revision=1, content_fingerprint="0" * 64)
    unresolved_facts = FactView(
        company_id=COMPANY_ID,
        decision_ts=DECISION_TS,
        values={"revenue": 100},
        evidence_refs_by_fact={"revenue": (unresolved,)},
        reporting_period=ReportingPeriod(period_type="FY"),
        accounting_scope=AccountingScope(),
    )
    wrong_cutoff_facts = FactView(
        company_id=COMPANY_ID,
        decision_ts=DECISION_TS - timedelta(days=1),
        values={},
        evidence_refs_by_fact={},
        reporting_period=ReportingPeriod(period_type="FY"),
        accounting_scope=AccountingScope(),
    )
    kwargs = dict(
        run_id="run:reject-unbound",
        company=CompanyRef(company_id=COMPANY_ID),
        decision_ts=DECISION_TS,
        baseline=_baseline(),
        evidence=view,
    )

    with pytest.raises(ValidationError, match="company"):
        ResearchContext(facts=other_company_facts, **kwargs)
    with pytest.raises(ValidationError, match="does not resolve"):
        ResearchContext(facts=unresolved_facts, **kwargs)
    with pytest.raises(ValidationError, match="cutoff"):
        ResearchContext(facts=wrong_cutoff_facts, **kwargs)


def test_research_context_rejects_a_fact_value_not_supported_by_its_evidence_ref():
    evidence = _evidence(revision=1, publish_ts=DECISION_TS, value=100)
    view = EvidenceView([evidence], company_id=COMPANY_ID, decision_ts=DECISION_TS)
    unsupported_facts = FactView(
        company_id=COMPANY_ID,
        decision_ts=DECISION_TS,
        values={"revenue": 999},
        evidence_refs_by_fact={"revenue": view.refs()},
        reporting_period=ReportingPeriod(period_type="FY"),
        accounting_scope=AccountingScope(),
    )

    with pytest.raises(ValidationError, match="does not support fact value"):
        ResearchContext(
            run_id="run:unsupported-fact",
            company=CompanyRef(company_id=COMPANY_ID),
            decision_ts=DECISION_TS,
            baseline=_baseline(),
            evidence=view,
            facts=unsupported_facts,
        )


def test_research_context_rejects_unbound_evidence_sources():
    class RepositoryEvidenceSource:
        def as_of(self, decision_ts: datetime) -> list[Evidence]:
            return [_evidence(revision=1, publish_ts=decision_ts, value=100)]

    facts = FactView(
        company_id=COMPANY_ID,
        decision_ts=DECISION_TS,
        values={},
        evidence_refs_by_fact={},
        reporting_period=ReportingPeriod(period_type="FY"),
        accounting_scope=AccountingScope(),
    )
    with pytest.raises(ValidationError):
        ResearchContext(
            run_id="run:unbound-source",
            company=CompanyRef(company_id=COMPANY_ID),
            decision_ts=DECISION_TS,
            baseline=_baseline(),
            evidence=RepositoryEvidenceSource(),
            facts=facts,
        )
