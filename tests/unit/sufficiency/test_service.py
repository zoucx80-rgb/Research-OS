from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from research_os.contracts.artifact_values import (
    AssumptionRef,
    ValuationExecution,
    ValuationReconciliation,
    ValuationResult,
)
from research_os.contracts.artifacts import ArtifactStore, ArtifactWrite
from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.forecasting.contracts import (
    ForecastBenchmarkEvidence,
    ForecastMetricEvidence,
    ForecastStabilityEvidence,
)
from research_os.period.models import ReportingPeriod
from research_os.runtime.core_artifacts import (
    FINANCIAL_TEMPORAL_ANALYSIS,
    FORECAST_BENCHMARK_EVIDENCE,
    VALUATION_EXECUTION,
    VALUATION_MARKET_GAP,
    VALUATION_RECONCILIATION,
    build_core_artifact_catalog,
)
from research_os.runtime.state import ResearchStateView
from research_os.sufficiency.models import (
    DomainSufficiencyAssessment,
    MaterialResearchGap,
    ResearchSufficiencyAssessment,
)
from research_os.sufficiency.service import ResearchSufficiencyEvaluator
from research_os.temporal.models import (
    FinancialPeriodObservation,
    FinancialTemporalAnalysis,
    MetricTemporalAssessment,
)
from research_os.temporal.service import TemporalAnalysisService
from research_os.valuation.market import ValuationMarketGap


DECISION_TS = datetime(2026, 9, 4, tzinfo=timezone.utc)


def _observation(year: int, value: str) -> FinancialPeriodObservation:
    return FinancialPeriodObservation(
        metric_id="revenue",
        reporting_period=ReportingPeriod(
            period_type="FY",
            period_start=date(year, 1, 1),
            period_end=date(year, 12, 31),
            period_days=366 if year % 4 == 0 else 365,
            is_cumulative=True,
        ),
        period_kind="FLOW",
        value=Decimal(value),
        unit="CNY",
        accounting_scope=AccountingScope(consolidation="consolidated"),
        value_kind="reported",
        comparison_basis="YOY_PERIOD",
        available_ts=datetime(year + 1, 3, 31, tzinfo=timezone.utc),
        evidence_refs=(
            EvidenceRef(
                evidence_id=f"ev:revenue:{year}",
                revision=1,
                content_fingerprint=("a" if year == 2024 else "b") * 64,
            ),
        ),
    )


def _assumption_observation(year: int, value: str) -> FinancialPeriodObservation:
    payload = _observation(year, value).model_dump()
    payload.update(
        value_kind="derived",
        evidence_refs=(),
        assumption_refs=(
            AssumptionRef(
                assumption_key="assumption:derived-revenue",
                assumption_version="1.0.0",
                content_fingerprint="c" * 64,
            ),
        ),
    )
    return FinancialPeriodObservation.model_validate(payload)


def _state(*observations: FinancialPeriodObservation) -> ResearchStateView:
    analysis = TemporalAnalysisService().analyze(
        tuple(observations),
        decision_ts=DECISION_TS,
    )
    return _state_from_analysis(analysis)


def _state_from_analysis(analysis: FinancialTemporalAnalysis) -> ResearchStateView:
    catalog = build_core_artifact_catalog()
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            key=FINANCIAL_TEMPORAL_ANALYSIS,
            value=analysis,
            producer_id="test:temporal",
            evidence_refs=analysis.evidence_refs,
        )
    )
    return ResearchStateView(store.freeze())


def _state_with_forecast(forecast: ForecastBenchmarkEvidence) -> ResearchStateView:
    catalog = build_core_artifact_catalog()
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            key=FINANCIAL_TEMPORAL_ANALYSIS,
            value=TemporalAnalysisService().analyze(
                (_observation(2024, "100"), _observation(2025, "110")),
                decision_ts=DECISION_TS,
            ),
            producer_id="test:temporal",
        )
    )
    store.write(
        ArtifactWrite(
            key=FORECAST_BENCHMARK_EVIDENCE,
            value=forecast,
            producer_id="test:forecast",
            evidence_refs=forecast.evidence_refs,
        )
    )
    return ResearchStateView(store.freeze())


def test_forecast_sufficiency_requires_oos_benchmark() -> None:
    reference = _observation(2025, "110").evidence_refs[0]
    result = ResearchSufficiencyEvaluator().evaluate(
        _state_with_forecast(
            ForecastBenchmarkEvidence(
                domain_status="INSUFFICIENT_EVIDENCE",
                model_key="ols:revenue",
                benchmark_key="naive:last_value",
                out_of_sample=False,
                pit_compliant=True,
                reason_codes=("INSUFFICIENT_OBSERVATIONS",),
                evidence_refs=(reference,),
            )
        )
    )

    domain = result.require_domain("forecast")
    assert domain.benchmark_coverage == "MISSING"
    assert domain.model_executability == "BLOCKED"
    assert "INSUFFICIENT_OBSERVATIONS" in domain.why_unknown
    assert "forecast:INSUFFICIENT_OBSERVATIONS" in result.blocking_gap_keys


def test_complete_forecast_evidence_is_executable_even_when_model_is_not_promoted() -> None:
    reference = _observation(2025, "110").evidence_refs[0]
    metrics = tuple(
        ForecastMetricEvidence(
            metric_name=name,
            value=Decimal(value),
            evidence_refs=(reference,),
        )
        for name, value in (
            ("MAE", "0.2"),
            ("RMSE", "0.3"),
            ("DIRECTION_ACCURACY", "0.5"),
            ("INTERVAL_COVERAGE", "0.9"),
        )
    )
    result = ResearchSufficiencyEvaluator().evaluate(
        _state_with_forecast(
            ForecastBenchmarkEvidence(
                domain_status="SUPPORTED",
                model_key="ols:revenue",
                benchmark_key="naive:last_value",
                benchmark_version="1.0.0",
                sample_count=6,
                fold_count=3,
                out_of_sample=True,
                pit_compliant=True,
                metrics=metrics,
                stability_windows=(
                    ForecastStabilityEvidence(
                        window_key="fold:1",
                        model_mae=Decimal("0.2"),
                        benchmark_mae=Decimal("0.1"),
                        evidence_refs=(reference,),
                    ),
                ),
                stable=False,
                current_stage="experimental",
                next_stage="experimental",
                promotion_reason="model did not beat registered benchmark",
                evidence_refs=(reference,),
            )
        )
    )

    domain = result.require_domain("forecast")
    assert domain.coverage == "COMPLETE"
    assert domain.benchmark_coverage == "COMPLETE"
    assert domain.model_executability == "EXECUTABLE"
    assert domain.material_gaps == ()
    assert result.overall_status == "SUFFICIENT"


def test_valuation_sufficiency_requires_controlled_execution_and_market_comparison() -> None:
    reference = _observation(2025, "110").evidence_refs[0]
    catalog = build_core_artifact_catalog()
    store = ArtifactStore(catalog)
    temporal = TemporalAnalysisService().analyze(
        (_observation(2024, "100"), _observation(2025, "110")),
        decision_ts=DECISION_TS,
    )
    for key, value in (
        (FINANCIAL_TEMPORAL_ANALYSIS, temporal),
        (
            VALUATION_EXECUTION,
            ValuationExecution(
                domain_status="SUPPORTED",
                execution_source="CONTROLLED",
                validation_status="PASS",
                selected_model="pe",
                results=(
                    ValuationResult(
                        model_key="pe",
                        status="SUPPORTED",
                        formula_version="pe@1.0.0",
                        value=Decimal("20"),
                        unit="CNY/share",
                        evidence_refs=(reference,),
                    ),
                ),
                evidence_refs=(reference,),
            ),
        ),
        (
            VALUATION_RECONCILIATION,
            ValuationReconciliation(
                domain_status="SUPPORTED",
                reconciliation_status="INTERSECTION",
                method="mathematical_intersection",
                low=Decimal("18"),
                high=Decimal("22"),
                included_range_keys=("range:1", "range:2"),
                evidence_refs=(reference,),
            ),
        ),
        (
            VALUATION_MARKET_GAP,
            ValuationMarketGap(
                domain_status="SUPPORTED",
                reconciliation_key="INTERSECTION:mathematical_intersection",
                market_anchor_security_id="300034.SZ",
                market_anchor_observed_ts=DECISION_TS,
                market_value=Decimal("12"),
                model_low=Decimal("18"),
                model_high=Decimal("22"),
                gap_low=Decimal("6"),
                gap_high=Decimal("10"),
                currency="CNY",
                valuation_basis="per_share",
                state="UNDERVALUED",
                comparison_status="PASS",
                evidence_refs=(reference,),
            ),
        ),
    ):
        store.write(
            ArtifactWrite(
                key=key,
                value=value,
                producer_id="test:sufficiency",
                evidence_refs=getattr(value, "evidence_refs", ()),
            )
        )

    result = ResearchSufficiencyEvaluator().evaluate(ResearchStateView(store.freeze()))

    domain = result.require_domain("valuation")
    assert domain.coverage == "COMPLETE"
    assert domain.model_executability == "EXECUTABLE"
    assert domain.known_items == (
        "market_comparison:UNDERVALUED",
        "model_execution:pe",
        "reconciliation:INTERSECTION",
    )
    assert domain.material_gaps == ()


def test_sufficiency_explains_upgrade_evidence_for_single_period() -> None:
    result = ResearchSufficiencyEvaluator().evaluate(_state(_observation(2025, "110")))

    temporal = result.require_domain("financial_temporal")
    assert result.overall_status == "INSUFFICIENT_EVIDENCE"
    assert temporal.coverage == "PARTIAL"
    assert temporal.evidence_quality == "COMPLETE"
    assert temporal.temporal_coverage == "MISSING"
    assert temporal.known_items == ("observation:revenue",)
    assert temporal.unknown_items == ("comparable_trend:revenue",)
    assert temporal.why_unknown == ("revenue:INSUFFICIENT_COMPARABLE_POINTS",)
    assert temporal.upgrade_evidence_requirements == (
        "add a comparable revenue period with explicit basis and revision-bound lineage",
    )
    assert temporal.material_gaps[0].required_evidence == (
        "comparable revenue period",
        "explicit comparison basis",
        "revision-bound lineage",
    )
    assert result.blocking_gap_keys == (
        "financial_temporal:revenue:INSUFFICIENT_COMPARABLE_POINTS",
    )


def test_comparable_temporal_evidence_is_sufficient() -> None:
    result = ResearchSufficiencyEvaluator().evaluate(
        _state(_observation(2024, "100"), _observation(2025, "110"))
    )

    temporal = result.require_domain("financial_temporal")
    assert result.overall_status == "SUFFICIENT"
    assert result.domain_status == "SUPPORTED"
    assert result.blocking_gap_keys == ()
    assert temporal.coverage == "COMPLETE"
    assert temporal.temporal_coverage == "COMPLETE"
    assert temporal.known_items == ("comparable_trend:revenue", "observation:revenue")
    assert temporal.unknown_items == ()


def test_assumption_only_temporal_lineage_is_limited_not_complete_evidence() -> None:
    result = ResearchSufficiencyEvaluator().evaluate(
        _state(
            _assumption_observation(2024, "100"),
            _assumption_observation(2025, "110"),
        )
    )

    domain = result.require_domain("financial_temporal")
    assert result.overall_status == "LIMITED"
    assert result.domain_status == "SUPPORTED"
    assert domain.temporal_coverage == "COMPLETE"
    assert domain.evidence_quality == "PARTIAL"


def test_supported_temporal_result_without_lineage_remains_insufficient() -> None:
    analysis = FinancialTemporalAnalysis(
        domain_status="SUPPORTED",
        assessments=(
            MetricTemporalAssessment(
                metric_id="revenue",
                unit="CNY",
                point_count=2,
                comparable_point_count=2,
                comparison_status="PASS",
            ),
        ),
        temporal_coverage="SUFFICIENT",
    )

    result = ResearchSufficiencyEvaluator().evaluate(_state_from_analysis(analysis))

    domain = result.require_domain("financial_temporal")
    assert result.overall_status == "INSUFFICIENT_EVIDENCE"
    assert domain.evidence_quality == "MISSING"
    assert domain.unknown_items == (
        "comparable_financial_trends",
        "lineage:financial_temporal",
    )
    assert domain.why_unknown == (
        "LINEAGE_MISSING",
        "TEMPORAL_OBSERVATIONS_MISSING",
    )
    assert result.blocking_gap_keys == (
        "financial_temporal:LINEAGE_MISSING",
        "financial_temporal:TEMPORAL_OBSERVATIONS_MISSING",
    )


def test_empty_temporal_artifact_names_missing_period_evidence() -> None:
    result = ResearchSufficiencyEvaluator().evaluate(_state())

    domain = result.require_domain("financial_temporal")
    assert result.overall_status == "INSUFFICIENT_EVIDENCE"
    assert domain.coverage == "MISSING"
    assert domain.unknown_items == (
        "comparable_financial_trends",
        "lineage:financial_temporal",
    )
    assert domain.why_unknown == (
        "LINEAGE_MISSING",
        "TEMPORAL_OBSERVATIONS_MISSING",
    )
    assert result.blocking_gap_keys == (
        "financial_temporal:LINEAGE_MISSING",
        "financial_temporal:TEMPORAL_OBSERVATIONS_MISSING",
    )


def test_sufficiency_contracts_canonicalize_domains_and_reject_duplicate_gaps() -> None:
    first_gap = MaterialResearchGap(
        gap_key="gap:a",
        domain_id="a",
        reason_code="MISSING_A",
        description="A is missing",
        required_evidence=("evidence a",),
    )
    domain_a = DomainSufficiencyAssessment(
        domain_id="a",
        coverage="MISSING",
        evidence_quality="MISSING",
        temporal_coverage="NOT_APPLICABLE",
        benchmark_coverage="NOT_APPLICABLE",
        peer_coverage="NOT_APPLICABLE",
        model_executability="NOT_APPLICABLE",
        known_items=(),
        unknown_items=("a",),
        why_unknown=("MISSING_A",),
        upgrade_evidence_requirements=("evidence a",),
        material_gaps=(first_gap,),
    )
    domain_b = domain_a.model_copy(
        update={
            "domain_id": "b",
            "material_gaps": (),
            "unknown_items": ("b",),
        }
    )

    assessment = ResearchSufficiencyAssessment(
        overall_status="INSUFFICIENT_EVIDENCE",
        domains=(domain_b, domain_a),
        blocking_gap_keys=("gap:a",),
    )

    assert tuple(item.domain_id for item in assessment.domains) == ("a", "b")
    assert assessment.require_domain("b") == domain_b
    with pytest.raises(KeyError, match="unknown sufficiency domain"):
        assessment.require_domain("missing")
    duplicate_gap_payload = domain_a.model_dump()
    duplicate_gap_payload["material_gaps"] = (first_gap, first_gap)
    with pytest.raises(ValidationError, match="material gap identities must be unique"):
        DomainSufficiencyAssessment.model_validate(duplicate_gap_payload)
