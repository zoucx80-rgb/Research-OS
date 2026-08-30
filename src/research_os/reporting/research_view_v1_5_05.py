from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field

from research_os.reporting.research_view import (
    HumanReadableResearchView as _BaseResearchView,
    ResearchViewPresenter as _BaseResearchViewPresenter,
)
from research_os.reporting.semantics import SemanticValue
from research_os.runtime.result import ResearchRunResult


class HumanReadableExpectationGap(SemanticValue.__base__):
    model_config = ConfigDict(frozen=True)

    metric: str
    direction: SemanticValue
    market_value: float | None = None
    market_range_low: float | None = None
    market_range_high: float | None = None
    market_direction: str | None = None
    os_value: float | None = None
    os_range_low: float | None = None
    os_range_high: float | None = None
    os_direction: str | None = None
    magnitude: float | None = None
    unit: str | None = None
    comparison_basis: str | None = None
    source_count: int | None = None
    source_quality: float | None = None
    age_days: int | None = None
    post_event_consensus: bool | None = None
    limitation: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class HumanReadableValuationResult(SemanticValue.__base__):
    model_config = ConfigDict(frozen=True)

    currency: str
    valuation_date: Any = None
    equity_value: float | None = None
    enterprise_value: float | None = None
    per_share_value: float | None = None
    bear_case: float | None = None
    base_case: float | None = None
    bull_case: float | None = None
    primary_range_low: float | None = None
    primary_range_high: float | None = None
    current_price: float | None = None
    implied_upside_downside: float | None = None
    method_result: dict[str, Any] = Field(default_factory=dict)
    sensitivities: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    assumption_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class HumanReadableMonitoring(SemanticValue.__base__):
    model_config = ConfigDict(frozen=True)

    next_verification_event: str = ""
    conviction_up_conditions: list[str] = Field(default_factory=list)
    thesis_broken_conditions: list[str] = Field(default_factory=list)
    key_metrics: list[str] = Field(default_factory=list)


class HumanReadableResearchView(_BaseResearchView):
    model_config = ConfigDict(frozen=True)

    expectation_gap: HumanReadableExpectationGap | None = None
    valuation_result: HumanReadableValuationResult | None = None
    monitoring: HumanReadableMonitoring | None = None
    presentation_limitations: list[str] = Field(default_factory=list)
    presentation_version: str = "professional-research-view@1.3.0"


class ResearchViewPresenter(_BaseResearchViewPresenter):
    """v1.5.05 additive projection; all research state remains canonical upstream."""

    version = "professional-research-view@1.3.0"

    _EXPECTATION_GAP_DIRECTIONS = {
        "ABOVE": (
            "Research OS 观点高于市场预期",
            "现有规范化证据显示 Research OS 观点高于可比市场预期。",
        ),
        "BELOW": (
            "Research OS 观点低于市场预期",
            "现有规范化证据显示 Research OS 观点低于可比市场预期。",
        ),
        "IN_LINE": (
            "Research OS 观点与市场预期大致一致",
            "现有规范化证据未显示具有方向性的预期差。",
        ),
        "MIXED": (
            "市场预期差方向不明确",
            "当前预期证据不足以形成单一方向的预期差。",
        ),
    }

    def _expectation_gap(self, item) -> HumanReadableExpectationGap | None:
        if item is None:
            return None
        return HumanReadableExpectationGap(
            metric=str(self._get(item, "metric", "")),
            direction=self._semantic(
                self._get(item, "direction", "MIXED"),
                self._EXPECTATION_GAP_DIRECTIONS,
                "市场预期差方向尚未配置中文说明",
            ),
            market_value=self._get(item, "market_value"),
            market_range_low=self._get(item, "market_range_low"),
            market_range_high=self._get(item, "market_range_high"),
            market_direction=self._get(item, "market_direction"),
            os_value=self._get(item, "os_value"),
            os_range_low=self._get(item, "os_range_low"),
            os_range_high=self._get(item, "os_range_high"),
            os_direction=self._get(item, "os_direction"),
            magnitude=self._get(item, "magnitude"),
            unit=self._get(item, "unit"),
            comparison_basis=self._get(item, "comparison_basis"),
            source_count=self._get(item, "source_count"),
            source_quality=self._get(item, "source_quality"),
            age_days=self._get(item, "age_days"),
            post_event_consensus=self._get(item, "post_event_consensus"),
            limitation=self._get(item, "limitation"),
            evidence_ids=list(self._get(item, "evidence_ids", []) or []),
        )

    def _valuation_result(self, item) -> HumanReadableValuationResult | None:
        if item is None:
            return None
        return HumanReadableValuationResult(
            currency=str(self._get(item, "currency", "")),
            valuation_date=self._get(item, "valuation_date"),
            equity_value=self._get(item, "equity_value"),
            enterprise_value=self._get(item, "enterprise_value"),
            per_share_value=self._get(item, "per_share_value"),
            bear_case=self._get(item, "bear_case"),
            base_case=self._get(item, "base_case"),
            bull_case=self._get(item, "bull_case"),
            primary_range_low=self._get(item, "primary_range_low"),
            primary_range_high=self._get(item, "primary_range_high"),
            current_price=self._get(item, "current_price"),
            implied_upside_downside=self._get(item, "implied_upside_downside"),
            method_result=dict(self._get(item, "method_result", {}) or {}),
            sensitivities=list(self._get(item, "sensitivities", []) or []),
            evidence_ids=list(self._get(item, "evidence_ids", []) or []),
            assumption_ids=list(self._get(item, "assumption_ids", []) or []),
            limitations=list(self._get(item, "limitations", []) or []),
        )

    @staticmethod
    def _monitoring(base: _BaseResearchView) -> HumanReadableMonitoring | None:
        broken = [
            falsifier.explanation
            for thesis in base.theses
            for falsifier in thesis.falsifiers
            if falsifier.explanation
        ]
        key_metrics = list(
            dict.fromkeys(
                falsifier.metric_label
                for thesis in base.theses
                for falsifier in thesis.falsifiers
                if falsifier.metric_label
            )
        )
        next_event = base.decision_summary.next_verification_event
        if not broken and not next_event:
            return None
        return HumanReadableMonitoring(
            next_verification_event=next_event,
            conviction_up_conditions=[],
            thesis_broken_conditions=broken,
            key_metrics=key_metrics,
        )

    @staticmethod
    def _presentation_limitations(result: ResearchRunResult) -> list[str]:
        if not getattr(result.business_model, "lease_heavy", False):
            return []
        return [
            "使用权资产或租赁负债具有重要性；当前报告未计算租赁调整后的资本回报或估值，"
            "因此不应仅凭固定资产较低或经营现金流较高推断轻资产、低资本占用或优异现金转化。"
        ]

    def build(
        self,
        result: ResearchRunResult,
        locale: str = _BaseResearchViewPresenter._SUPPORTED_LOCALE,
    ) -> HumanReadableResearchView:
        base = super().build(result, locale=locale)
        data = base.model_dump(mode="python")
        data.update(
            expectation_gap=self._expectation_gap(result.artifacts.get("expectation.gap")),
            valuation_result=self._valuation_result(result.artifacts.get("valuation.result")),
            monitoring=self._monitoring(base),
            presentation_limitations=self._presentation_limitations(result),
            presentation_version=self.version,
        )
        return HumanReadableResearchView.model_validate(data)
