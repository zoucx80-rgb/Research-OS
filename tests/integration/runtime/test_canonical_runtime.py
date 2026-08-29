from datetime import datetime, timezone

from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchInputs,
    ResearchOptions,
)
from research_os.runtime.factory import ResearchRuntimeFactory


def _versions():
    return {
        "research_os_version": "1.4.0",
        "dataset_version": "synthetic@1",
        "parser_version": "synthetic@1",
        "formula_version": "synthetic@1",
        "router_version": "router@1.0.0",
        "kpi_pack_version": "auto",
        "driver_model_version": "driver@1",
        "forecast_version": "none",
        "valuation_version": "none",
        "report_version": "runtime@1",
        "core_api_version": "1.0",
    }


def _context():
    publish_ts = datetime(2026, 8, 1, tzinfo=timezone.utc)
    facts = {
        "business_description": "precision manufacturing",
        "revenue": 1000.0,
        "net_profit_parent": 50.0,
        "assets_begin": 800.0,
        "assets_end": 900.0,
        "equity_begin": 400.0,
        "equity_end": 450.0,
        "period_type": "FY",
    }
    evidence = [
        Evidence(
            evidence_id=f"ev:{key}",
            company_id="synthetic:manufacturer",
            evidence_type=EvidenceType.FILING_FACT,
            publish_ts=publish_ts,
            ingested_at=publish_ts,
            value=value,
            source_table=key,
            confidence_grade=ConfidenceGrade.A,
            verification_status=VerificationStatus.PRIMARY_VERIFIED,
        )
        for key, value in facts.items()
    ]
    return ResearchContext(
        run_id="run:canonical:manufacturer",
        company=CompanyRef(company_id="synthetic:manufacturer"),
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            research_os_version="1.4.0",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(
            values=facts,
            evidence_by_fact={key: [f"ev:{key}"] for key in facts},
        ),
        options=ResearchOptions(),
    )


def test_canonical_runtime_auto_resolves_and_returns_one_result_contract():
    runtime = ResearchRuntimeFactory.default()
    result = runtime.run_context(_context(), ResearchInputs(versions=_versions()))

    assert result.business_model.primary_model == "manufacturing"
    assert [p.plugin_id for p in result.strategy_resolution.industry_plugins] == [
        "industry:manufacturing"
    ]
    assert result.module_results["core:industry-kpi"].status == "PASS"
    assert result.artifacts["kpi.pack_ids"] == ["manufacturing"]
    assert result.completion.final_status == "INCOMPLETE"
    assert result.component_fingerprints
    assert result.snapshot.payload_hash


def test_same_input_has_stable_payload_hash_and_component_fingerprints():
    runtime = ResearchRuntimeFactory.default()
    context = _context()
    inputs = ResearchInputs(versions=_versions())

    first = runtime.run_context(context, inputs)
    second = runtime.run_context(context, inputs)

    assert first.snapshot.snapshot_id != second.snapshot.snapshot_id
    assert first.snapshot.payload_hash == second.snapshot.payload_hash
    assert first.component_fingerprints == second.component_fingerprints
