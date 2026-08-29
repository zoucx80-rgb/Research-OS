from datetime import datetime, timedelta, timezone

from research_os.domain.evidence import Evidence
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchInputs,
    ResearchOptions,
    ResearchRuntimeFactory,
)


def _facts():
    return {
        "business_description": "electronic component distribution",
        "revenue": 1000.0,
        "cogs": 970.0,
        "gross_profit": 30.0,
        "gross_margin": 0.03,
        "avg_ar": 160.0,
        "avg_inventory": 140.0,
        "avg_ap": 80.0,
        "ar": 180.0,
        "inventory": 150.0,
        "ap": 90.0,
        "delta_nwc": 80.0,
        "delta_revenue": 200.0,
        "delta_debt": 60.0,
        "delta_equity": 0.0,
        "ocf": 20.0,
        "net_profit": 25.0,
        "nopat": 24.0,
        "avg_invested_capital": 300.0,
        "period_type": "FY",
    }


def _versions():
    return {
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


def _context(*, facts=None, evidence=None, lineage=None):
    decision_ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
    values = facts or _facts()
    items = evidence or [
        Evidence(
            evidence_id=f"ev:{key}",
            company_id="synthetic:distributor",
            evidence_type="calculated_metric",
            source_table=key,
            value=value,
            publish_ts=decision_ts,
            ingested_at=decision_ts,
            confidence_grade="B",
            verification_status="PRIMARY_VERIFIED",
        )
        for key, value in values.items()
    ]
    return ResearchContext(
        run_id="run:canonical:distributor",
        company=CompanyRef(company_id="synthetic:distributor"),
        decision_ts=decision_ts,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            research_os_version="1.4.0",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(items),
        facts=LegacyFactView(
            values=values,
            evidence_by_fact=lineage or {key: [f"ev:{key}"] for key in values},
        ),
        options=ResearchOptions(),
    )


def test_canonical_distributor_run_is_auditable_and_carries_metric_lineage():
    result = ResearchRuntimeFactory.default().run_context(
        _context(), ResearchInputs(versions=_versions())
    )

    assert result.business_model.primary_model == "distributor"
    assert result.artifacts["kpi.pack_ids"] == ["distributor"]
    assert result.artifacts["thesis.items"][0].anti_thesis
    ccc = next(m for m in result.artifacts["kpi.metrics"] if m.metric_id == "ccc_days")
    assert {"ev:avg_ar", "ev:revenue", "ev:avg_inventory", "ev:cogs", "ev:avg_ap"} <= set(ccc.evidence_ids)
    assert result.snapshot.payload_hash
    assert result.snapshot.payload["completion"]["final_status"] == result.completion.final_status


def test_future_only_fact_support_fails_pit_lineage_and_blocks_completion():
    decision_ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
    facts = _facts()
    facts["revenue"] = 999.0
    evidence = []
    for key, value in _facts().items():
        evidence.append(Evidence(
            evidence_id=f"ev:{key}:old",
            company_id="synthetic:distributor",
            evidence_type="calculated_metric",
            source_table=key,
            value=value,
            publish_ts=decision_ts,
            ingested_at=decision_ts,
            confidence_grade="B",
            verification_status="PRIMARY_VERIFIED",
        ))
    evidence.append(Evidence(
        evidence_id="ev:revenue:future",
        company_id="synthetic:distributor",
        evidence_type="calculated_metric",
        source_table="revenue",
        value=999.0,
        publish_ts=decision_ts + timedelta(days=1),
        ingested_at=decision_ts + timedelta(days=1),
        confidence_grade="B",
        verification_status="PRIMARY_VERIFIED",
    ))
    lineage = {key: [f"ev:{key}:old"] for key in facts}
    lineage["revenue"] = ["ev:revenue:future"]

    result = ResearchRuntimeFactory.default().run_context(
        _context(facts=facts, evidence=evidence, lineage=lineage),
        ResearchInputs(versions=_versions()),
    )

    assert result.module_results["core:pit-lineage"].status == "FAIL"
    assert result.completion.final_status == "INCOMPLETE"
    assert any("revenue" in item for item in result.module_results["core:pit-lineage"].diagnostics)
