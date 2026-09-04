from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel

from research_os.completion.models import ExecutionCompletionResult
from research_os.contracts.artifacts import ArtifactKey, ArtifactSnapshot
from research_os.readiness.models import (
    DimensionStatus,
    ReadinessDimension,
    ReadinessRequirement,
    ResearchReadinessAssessment,
)


STANDARD_READINESS_DIMENSIONS = (
    "time_series",
    "operating_evidence",
    "cash_flow",
    "consensus",
    "peers",
    "sensitivity",
    "monitoring_events",
    "prior_run_validation",
    "methodology",
)


def _standard_requirements() -> tuple[ReadinessRequirement, ...]:
    from research_os.runtime.core_artifacts import (
        CASH_FLOW_QUALITY_BRIDGE,
        EXPECTATION_CONSENSUS_DISTRIBUTION,
        FINANCIAL_TIME_SERIES,
        METHODOLOGY_DISCLOSURE,
        MONITORING_PLAN,
        MONITORING_PRIOR_RUN_REVIEW,
        PEERS_NORMALIZED,
        RESEARCH_OPERATING_EVIDENCE,
        SCENARIO_SENSITIVITIES,
    )

    keys: dict[str, ArtifactKey[Any]] = {
        "time_series": FINANCIAL_TIME_SERIES,
        "operating_evidence": RESEARCH_OPERATING_EVIDENCE,
        "cash_flow": CASH_FLOW_QUALITY_BRIDGE,
        "consensus": EXPECTATION_CONSENSUS_DISTRIBUTION,
        "peers": PEERS_NORMALIZED,
        "sensitivity": SCENARIO_SENSITIVITIES,
        "monitoring_events": MONITORING_PLAN,
        "prior_run_validation": MONITORING_PRIOR_RUN_REVIEW,
        "methodology": METHODOLOGY_DISCLOSURE,
    }
    return tuple(
        ReadinessRequirement(
            dimension_id=dimension_id,
            artifact_keys=(keys[dimension_id],),
        )
        for dimension_id in STANDARD_READINESS_DIMENSIONS
    )


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, bytes, Sequence, Mapping)):
        return bool(value)
    if isinstance(value, BaseModel):
        return any(item not in (None, (), [], {}) for item in value.model_dump().values())
    return True


def _artifact_is_substantive(key: ArtifactKey[Any], value: Any) -> bool:
    """Apply domain-specific presence rules instead of counting model defaults."""

    if key.artifact_id == "monitoring.plan":
        return bool(getattr(value, "items", ()) or getattr(value, "next_verification_event", None))

    collection_fields = {
        "financial.time_series": "series",
        "research.operating_evidence": "observations",
        "expectation.consensus_distribution": "observations",
        "peers.normalized": "peers",
        "scenario.sensitivities": "cases",
        "monitoring.prior_run_review": "items",
    }
    collection_field = collection_fields.get(key.artifact_id)
    if collection_field is not None:
        return bool(getattr(value, collection_field, ()))

    if key.artifact_id == "cash_flow.quality_bridge":
        material_fields = (
            "net_profit",
            "operating_cash_flow",
            "working_capital_contribution",
            "other_adjustments",
            "capex_cash",
            "simplified_fcf",
        )
        return any(getattr(value, field, None) is not None for field in material_fields)

    if key.artifact_id == "methodology.disclosure":
        return any(
            getattr(value, field, ()) for field in ("policy_keys", "plugin_keys", "limitations")
        )

    return _present(value)


def _has_assumption_lineage(value: Any) -> bool:
    if isinstance(value, BaseModel):
        if "assumption_refs" in type(value).model_fields and bool(
            object.__getattribute__(value, "assumption_refs")
        ):
            return True
        return any(
            _has_assumption_lineage(getattr(value, field_name))
            for field_name in type(value).model_fields
        )
    if isinstance(value, Mapping):
        return any(_has_assumption_lineage(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_has_assumption_lineage(item) for item in value)
    return False


def _artifact_readiness_status(
    key: ArtifactKey[Any], artifacts: ArtifactSnapshot
) -> DimensionStatus:
    envelope = artifacts.envelope(key)
    if envelope is None:
        return "INCOMPLETE"
    domain_status = getattr(envelope.value, "domain_status", None)
    if domain_status == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    if domain_status == "INSUFFICIENT_EVIDENCE":
        return "INCOMPLETE"
    if not _artifact_is_substantive(key, envelope.value):
        return "INCOMPLETE"
    if envelope.evidence_refs or _has_assumption_lineage(envelope.value):
        return "PASS"
    return "INCOMPLETE"


class ResearchReadinessEvaluator:
    def __init__(
        self,
        requirements: Iterable[ReadinessRequirement] | None = None,
    ) -> None:
        configured = tuple(requirements) if requirements is not None else _standard_requirements()
        if len({item.dimension_id for item in configured}) != len(configured):
            raise ValueError("readiness requirements must have unique dimensions")
        self._requirements = tuple(sorted(configured, key=lambda item: item.dimension_id))

    def evaluate(
        self,
        completion: ExecutionCompletionResult,
        artifacts: ArtifactSnapshot,
    ) -> ResearchReadinessAssessment:
        dimensions = []
        for requirement in self._requirements:
            status: DimensionStatus
            artifact_statuses = tuple(
                _artifact_readiness_status(key, artifacts) for key in requirement.artifact_keys
            )
            if artifact_statuses and all(
                item in {"PASS", "NOT_APPLICABLE"} for item in artifact_statuses
            ):
                status = "PASS" if "PASS" in artifact_statuses else "NOT_APPLICABLE"
            else:
                status = "INCOMPLETE"
            dimensions.append(
                ReadinessDimension(
                    dimension_id=requirement.dimension_id,
                    status=status,
                    required_artifacts=tuple(key.artifact_id for key in requirement.artifact_keys),
                )
            )

        blocking = [item.dimension_id for item in dimensions if item.status == "INCOMPLETE"]
        if completion.final_status == "INCOMPLETE":
            blocking.append("execution_completion")
        blocking_tuple = tuple(sorted(set(blocking)))
        return ResearchReadinessAssessment(
            final_status="NOT_READY" if blocking_tuple else "READY",
            dimensions=tuple(dimensions),
            blocking_dimensions=blocking_tuple,
            execution_status=completion.final_status,
        )
