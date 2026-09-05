from __future__ import annotations

from decimal import Decimal

from research_os.contracts.evidence import EvidenceRef
from research_os.forecasting.contracts import (
    ForecastBenchmarkEvidence,
    ForecastMetricEvidence,
    ForecastStabilityEvidence,
)
from research_os.reporting.projectors import project_artifact


def _reference() -> EvidenceRef:
    return EvidenceRef(
        evidence_id="ev:forecast:report",
        revision=1,
        content_fingerprint="a" * 64,
    )


def _benchmark_evidence() -> ForecastBenchmarkEvidence:
    reference = _reference()
    return ForecastBenchmarkEvidence(
        domain_status="SUPPORTED",
        model_key="ols:revenue",
        target_metric="revenue_growth",
        horizon="FY+1",
        benchmark_key="naive:last_value",
        benchmark_version="1.0.0",
        sample_count=12,
        fold_count=3,
        out_of_sample=True,
        pit_compliant=True,
        metrics=tuple(
            ForecastMetricEvidence(
                metric_name=name,
                value=value,
                evidence_refs=(reference,),
            )
            for name, value in (
                ("MAE", Decimal("0.08")),
                ("RMSE", Decimal("0.1")),
                ("DIRECTION_ACCURACY", Decimal("0.75")),
                ("INTERVAL_COVERAGE", Decimal("0.9")),
            )
        ),
        benchmark_mae=Decimal("0.12"),
        improvement=Decimal("0.333333"),
        stability_windows=(
            ForecastStabilityEvidence(
                window_key="fold:1",
                model_mae=Decimal("0.08"),
                benchmark_mae=Decimal("0.12"),
                evidence_refs=(reference,),
            ),
        ),
        stable=True,
        current_stage="experimental",
        next_stage="candidate",
        promotion_reason="all promotion gates passed",
        applicability="annual comparable periods",
        model_boundary="linear explanatory forecast",
        caveats=("Limited cycle coverage.",),
        evidence_refs=(reference,),
    )


def test_forecast_projector_exposes_metrics_and_promotion_reason() -> None:
    projected = project_artifact("forecast.benchmark_evidence", _benchmark_evidence())

    assert projected.audit_only is False
    assert projected.title == "预测基准证据"
    assert projected.payload["样本外验证"] is True
    assert projected.payload["基准模型"] == "最近一期值"
    assert projected.payload["样本数"] == 12
    assert projected.payload["样本外折数"] == 3
    assert projected.payload["模型 MAE"] != "—"
    assert projected.payload["方向准确率"] != "—"
    assert projected.payload["晋级结论"] == "全部晋级门槛均已通过"
    assert projected.payload["适用范围"] == "annual comparable periods"
    assert projected.payload["模型边界"] == "linear explanatory forecast"


def test_insufficient_forecast_projection_names_upgrade_reasons() -> None:
    projected = project_artifact(
        "forecast.benchmark_evidence",
        ForecastBenchmarkEvidence(
            reason_codes=("EXPERIMENT_NOT_PROVIDED",),
        ),
    )

    assert projected.audit_only is False
    assert projected.payload["不足原因"] == ["未提供预测实验"]
