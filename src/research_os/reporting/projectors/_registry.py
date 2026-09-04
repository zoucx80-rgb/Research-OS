from __future__ import annotations

from typing import Any, Callable

from pydantic import JsonValue

from ._core import (
    _business_model,
    _capital,
    _cash_flow,
    _claims,
    _decision,
    _decision_provenance,
    _driver_graph,
    _financial_series,
    _funding,
    _metrics,
    _operating,
    _semantic_signals,
    _thesis,
)
from ._market import (
    _consensus_distribution,
    _expectation_gap,
    _expectation_quality,
    _expectation_snapshot,
    _forecast,
    _peers,
    _sensitivities,
    _valuation_execution,
    _valuation_reconciliation,
    _valuation_result,
    _valuation_routing,
)
from ._monitoring import _methodology, _monitoring, _prior_run, _readiness
from ._shared import ArtifactProjection, _ARTIFACT_META, _AUDIT_IDS, _AUDIT_PREFIXES, _python

_PROJECTORS: dict[str, Callable[[dict[str, Any]], JsonValue]] = {
    "decision.record": _decision,
    "decision.state_provenance": _decision_provenance,
    "business_model.profile": _business_model,
    "kpi.metrics": _metrics,
    "financial.time_series": _financial_series,
    "research.operating_evidence": _operating,
    "cash_flow.quality_bridge": _cash_flow,
    "capital.efficiency": _capital,
    "capital.funding_loop": _funding,
    "drivers.graph": _driver_graph,
    "thesis.portfolio": _thesis,
    "thesis.semantic_signal_assessment": _semantic_signals,
    "semantic.claims": _claims,
    "expectation.snapshot": _expectation_snapshot,
    "expectation.quality": _expectation_quality,
    "expectation.gap": _expectation_gap,
    "expectation.consensus_distribution": _consensus_distribution,
    "forecast.evaluation": _forecast,
    "peers.normalized": _peers,
    "valuation.routing": _valuation_routing,
    "valuation.execution": _valuation_execution,
    "valuation.result": _valuation_result,
    "valuation.reconciliation": _valuation_reconciliation,
    "scenario.sensitivities": _sensitivities,
    "monitoring.plan": _monitoring,
    "monitoring.prior_run_review": _prior_run,
    "research.readiness": _readiness,
    "methodology.disclosure": _methodology,
}


def _substantive(artifact_id: str, data: dict[str, Any]) -> bool:
    if artifact_id in {
        "decision.record",
        "decision.state_provenance",
        "business_model.profile",
        "research.readiness",
    }:
        return True
    if artifact_id == "methodology.disclosure":
        return bool(data.get("limitations"))
    if artifact_id == "expectation.quality":
        return bool(data.get("reason_codes")) or data.get("quality_status") not in {None, "UNKNOWN"}
    if artifact_id == "forecast.evaluation":
        return bool(data.get("model_key") or data.get("benchmark_key") or data.get("folds"))
    checks = {
        "kpi.metrics": ("metrics",),
        "financial.time_series": ("series",),
        "research.operating_evidence": ("observations",),
        "cash_flow.quality_bridge": (
            "net_profit",
            "operating_cash_flow",
            "capex_cash",
            "simplified_fcf",
        ),
        "capital.efficiency": ("roic", "incremental_roic", "iwcr"),
        "capital.funding_loop": ("reason_codes",),
        "drivers.graph": ("nodes", "edges"),
        "thesis.portfolio": ("primary", "supporting", "conflicting", "unresolved", "falsified"),
        "thesis.semantic_signal_assessment": ("signals",),
        "semantic.claims": ("claims",),
        "expectation.snapshot": ("vintage",),
        "expectation.gap": ("metric_id", "market_value", "os_value", "magnitude"),
        "expectation.consensus_distribution": (
            "observations",
            "source_count",
            "low",
            "median",
            "high",
        ),
        "peers.normalized": ("peers",),
        "valuation.routing": ("primary_model_keys", "secondary_model_keys"),
        "valuation.execution": ("results",),
        "valuation.result": ("value",),
        "valuation.reconciliation": ("low", "high", "included_range_keys"),
        "scenario.sensitivities": ("cases",),
        "monitoring.plan": ("items", "next_verification_event"),
        "monitoring.prior_run_review": ("items", "scored_count"),
    }
    return any(
        data.get(key) not in (None, "", [], (), {}, 0) for key in checks.get(artifact_id, ())
    )


def project_artifact(artifact_id: str, value: object) -> ArtifactProjection:
    if artifact_id.startswith(_AUDIT_PREFIXES) or artifact_id in _AUDIT_IDS:
        return ArtifactProjection(
            section_id="other", title=artifact_id, payload={}, audit_only=True
        )
    meta = _ARTIFACT_META.get(artifact_id)
    projector = _PROJECTORS.get(artifact_id)
    if meta is None or projector is None:
        return ArtifactProjection(
            section_id="other", title=artifact_id, payload={}, audit_only=True
        )
    data = _python(value)
    if not isinstance(data, dict):
        data = {"value": data}
    section_id, title = meta
    if not _substantive(artifact_id, data):
        return ArtifactProjection(section_id=section_id, title=title, payload={}, audit_only=True)
    return ArtifactProjection(
        section_id=section_id,
        title=title,
        payload=projector(data),
        audit_only=False,
    )
