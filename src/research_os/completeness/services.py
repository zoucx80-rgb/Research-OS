from __future__ import annotations

from statistics import median
from typing import Literal

from research_os.completeness.models import (
    CashFlowQualityBridge,
    CashFlowQualityInput,
    ConsensusDistribution,
    ConsensusObservation,
    PriorRunReview,
    PriorRunReviewInput,
    PriorRunReviewItem,
)


def build_cash_flow_quality_bridge(value: CashFlowQualityInput) -> CashFlowQualityBridge:
    simplified_fcf = None
    if value.operating_cash_flow is not None and value.capex_cash is not None:
        simplified_fcf = value.operating_cash_flow - value.capex_cash
    return CashFlowQualityBridge(
        net_profit=value.net_profit,
        operating_cash_flow=value.operating_cash_flow,
        working_capital_contribution=value.working_capital_contribution,
        other_adjustments=value.other_adjustments,
        capex_cash=value.capex_cash,
        simplified_fcf=simplified_fcf,
        unit=value.unit,
        evidence_ids=value.evidence_ids,
        assumption_ids=value.assumption_ids,
    )


def build_consensus_distribution(
    *,
    observations: tuple[ConsensusObservation, ...],
    decision_ts,
    metric: str,
    forecast_period: str,
) -> ConsensusDistribution:
    if any(item.publish_ts > decision_ts for item in observations):
        raise ValueError("post-decision consensus observation is not allowed")

    matching = [
        item
        for item in observations
        if item.metric == metric and item.forecast_period == forecast_period
    ]
    latest_by_source: dict[str, ConsensusObservation] = {}
    for item in matching:
        previous = latest_by_source.get(item.source_id)
        if previous is None or item.publish_ts > previous.publish_ts:
            latest_by_source[item.source_id] = item

    selected = list(latest_by_source.values())
    values = sorted(item.value for item in selected)
    source_ids = tuple(sorted(latest_by_source))
    evidence_ids = tuple(
        dict.fromkeys(
            evidence_id
            for item in selected
            for evidence_id in item.evidence_ids
            if evidence_id
        )
    )
    if not values:
        return ConsensusDistribution(
            metric=metric,
            forecast_period=forecast_period,
            source_ids=source_ids,
            evidence_ids=evidence_ids,
        )

    source_count = len(source_ids)
    low = values[0]
    high = values[-1]
    return ConsensusDistribution(
        metric=metric,
        forecast_period=forecast_period,
        source_count=source_count,
        low=low,
        median=float(median(values)),
        high=high,
        dispersion=high - low,
        breadth="single_source" if source_count == 1 else "multi_source",
        source_ids=source_ids,
        evidence_ids=evidence_ids,
    )


def build_prior_run_review(
    *, items: tuple[PriorRunReviewInput, ...]
) -> PriorRunReview:
    output: list[PriorRunReviewItem] = []
    for item in items:
        error = None
        absolute_error = None
        status: Literal["HIT", "MISS", "UNKNOWN"] = "UNKNOWN"
        if (
            item.predicted_value is not None
            and item.actual_value is not None
            and item.tolerance is not None
        ):
            error = item.actual_value - item.predicted_value
            absolute_error = abs(error)
            status = "HIT" if absolute_error <= item.tolerance else "MISS"
        evidence_ids = tuple(
            dict.fromkeys(
                [*item.prior_evidence_ids, *item.actual_evidence_ids]
            )
        )
        output.append(
            PriorRunReviewItem(
                item_id=item.item_id,
                prior_statement=item.prior_statement,
                metric=item.metric,
                period=item.period,
                predicted_value=item.predicted_value,
                actual_value=item.actual_value,
                tolerance=item.tolerance,
                error=error,
                absolute_error=absolute_error,
                status=status,
                evidence_ids=evidence_ids,
            )
        )

    scored = [item for item in output if item.status in {"HIT", "MISS"}]
    misses = [item for item in scored if item.status == "MISS"]
    candidates = ("review_missed_predictions",) if misses else ()
    return PriorRunReview(
        items=tuple(output),
        scored_count=len(scored),
        hit_count=sum(item.status == "HIT" for item in scored),
        miss_count=len(misses),
        process_change_candidates=candidates,
    )
