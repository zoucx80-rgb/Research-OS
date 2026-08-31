from __future__ import annotations

from datetime import date, timedelta

from research_os.thesis.models import Falsifier, Thesis
from research_os.thesis.semantic_signals import (
    DirectionalSignal,
    GrowthComparisonRule,
    SemanticSignalAssessment,
    assess_comparability,
)
from research_os.thesis.service import ThesisService as _LegacyThesisService


class SemanticThesisService:
    """Directionally safe signals plus an explicit thesis lifecycle.

    A mixed observation set is not a weakening thesis unless an explicit prior
    directional thesis exists. Cross-metric conclusions are opt-in through
    comparison rules and remain fail-closed on incompatible bases.
    """

    def __init__(
        self,
        *,
        comparison_rules: tuple[GrowthComparisonRule, ...] = (),
        prior_theses: tuple[Thesis, ...] = (),
    ):
        self.comparison_rules = comparison_rules
        self.prior_theses = prior_theses
        self._legacy_evaluator = _LegacyThesisService()

    @staticmethod
    def _by_metric(evidence):
        result = {}
        for item in evidence:
            key = item.source_table or item.evidence_id
            if key not in result:
                result[key] = item
        return result

    @staticmethod
    def _numeric(item):
        value = None if item is None else item.value
        return value if isinstance(value, (int, float)) else None

    @staticmethod
    def _directional_signal(item, *, metric: str, positive_label: str, negative_label: str):
        value = SemanticThesisService._numeric(item)
        if value is None or value == 0:
            return None
        positive = value > 0
        return DirectionalSignal(
            metric=metric,
            direction="POSITIVE" if positive else "NEGATIVE",
            semantic_label=positive_label if positive else negative_label,
            value=float(value),
            comparison_basis=getattr(item, "comparison_basis", None),
            evidence_ids=(item.evidence_id,),
            reason_code="DIRECTIONAL_METRIC_SIGN",
        )

    @staticmethod
    def _driver_evidence_ids(nodes) -> list[str]:
        result: list[str] = []
        for node in nodes:
            for evidence_id in node.evidence_ids:
                if evidence_id and evidence_id not in result:
                    result.append(evidence_id)
        return result

    def assess_signals(self, evidence) -> SemanticSignalAssessment:
        items = self._by_metric(evidence)
        signals: list[DirectionalSignal] = []
        comparisons = []

        directional_specs = (
            ("revenue_growth", "收入增长", "收入下降"),
            ("margin_change", "毛利率改善", "毛利率下降"),
            ("roic_change", "资本回报改善", "资本回报下降"),
            ("ocf_growth", "经营现金流改善", "经营现金流下降"),
        )
        for metric, positive_label, negative_label in directional_specs:
            signal = self._directional_signal(
                items.get(metric),
                metric=metric,
                positive_label=positive_label,
                negative_label=negative_label,
            )
            if signal is not None:
                signals.append(signal)

        ocf_item = items.get("ocf") or items.get("operating_cash_flow")
        ocf = self._numeric(ocf_item)
        if ocf is not None and ocf != 0:
            signals.append(
                DirectionalSignal(
                    metric="operating_cash_flow",
                    direction="POSITIVE" if ocf > 0 else "NEGATIVE",
                    semantic_label="经营现金流为正" if ocf > 0 else "经营现金流为负",
                    value=float(ocf),
                    comparison_basis=getattr(ocf_item, "comparison_basis", None),
                    evidence_ids=(ocf_item.evidence_id,),
                    reason_code="OCF_SIGN",
                )
            )

        for rule in self.comparison_rules:
            left = items.get(rule.left_metric)
            right = items.get(rule.right_metric)
            comparison = assess_comparability(rule=rule, left=left, right=right)
            comparisons.append(comparison)
            if comparison.status != "COMPARABLE":
                continue
            left_value = self._numeric(left)
            right_value = self._numeric(right)
            if left_value is None or right_value is None:
                continue
            if left_value - right_value > rule.spread_threshold:
                signals.append(
                    DirectionalSignal(
                        metric=f"{rule.left_metric}_vs_{rule.right_metric}",
                        direction="NEGATIVE",
                        semantic_label=rule.adverse_label,
                        value=float(left_value - right_value),
                        comparison_basis=comparison.left_basis,
                        evidence_ids=(left.evidence_id, right.evidence_id),
                        reason_code="EXPLICIT_GROWTH_SPREAD_RULE",
                    )
                )

        positive = tuple(item.semantic_label for item in signals if item.direction == "POSITIVE")
        negative = tuple(item.semantic_label for item in signals if item.direction == "NEGATIVE")
        if positive and negative:
            status = "MIXED"
        elif len(positive) >= 2:
            status = "SUPPORTED"
        else:
            status = "INSUFFICIENT"

        evidence_ids = tuple(
            dict.fromkeys(
                evidence_id
                for signal in signals
                for evidence_id in signal.evidence_ids
                if evidence_id
            )
        )
        return SemanticSignalAssessment(
            status=status,
            signals=tuple(signals),
            comparisons=tuple(comparisons),
            positive_signals=positive,
            negative_signals=negative,
            evidence_ids=evidence_ids,
        )

    @staticmethod
    def _next_check_date(evidence) -> date:
        return max(
            (item.publish_ts.date() for item in evidence),
            default=date.today(),
        ) + timedelta(days=100)

    @staticmethod
    def _driver_ids(drivers) -> list[str]:
        return [node.driver_id for node in drivers.nodes]

    def _financing_cash_quality_thesis(self, company_id, evidence, drivers):
        if not any(node.driver_type == "financing" for node in drivers.nodes):
            return None
        values = self._by_metric(evidence)
        falsifiers = [Falsifier(metric="ocf", operator="<", threshold=0)]
        if "funding_loop_debt_share" in values:
            falsifiers.append(
                Falsifier(
                    metric="funding_loop_debt_share",
                    operator=">=",
                    threshold=0.6,
                    description="新增营运资金对债务融资依赖较高",
                )
            )
        supporting_nodes = [
            node
            for node in drivers.nodes
            if node.driver_type in {"working_capital", "financing"}
        ]
        thesis = Thesis(
            thesis_id=f"{company_id}:cash-quality",
            company_id=company_id,
            title="Growth converts to cash",
            statement="Growth should improve cash generation rather than depend indefinitely on external funding.",
            mechanism="Revenue growth must translate through working-capital efficiency into operating cash flow.",
            anti_thesis="Growth remains dependent on inventory, receivables and external financing, so cash quality deteriorates.",
            status="active",
            supporting_drivers=[node.driver_id for node in supporting_nodes],
            supporting_evidence=self._driver_evidence_ids(supporting_nodes),
            falsifiers=falsifiers,
            verification_metrics=["ocf", "ccc_days", "funding_loop_debt_share"],
            next_check_date=self._next_check_date(evidence),
            confidence=0.7,
        )
        return self._legacy_evaluator.evaluate_existing(thesis, evidence)

    def evaluate(self, company_id, evidence, drivers):
        if self.prior_theses:
            return [
                self._legacy_evaluator.evaluate_existing(thesis, evidence)
                for thesis in self.prior_theses
            ]

        financing_thesis = self._financing_cash_quality_thesis(company_id, evidence, drivers)
        if financing_thesis is not None:
            return [financing_thesis]

        assessment = self.assess_signals(evidence)
        if assessment.status == "INSUFFICIENT":
            return []

        next_check = self._next_check_date(evidence)
        if assessment.status == "MIXED":
            return [
                Thesis(
                    thesis_id=f"{company_id}:operating-direction-unresolved",
                    company_id=company_id,
                    title="Operating direction unresolved",
                    statement=(
                        "Operating signals are mixed; wait for confirmation before "
                        "asserting a directional operating trend."
                    ),
                    mechanism=(
                        "Positive operating or cash evidence is offset by contradictory "
                        "margin, capital-efficiency or working-capital evidence."
                    ),
                    anti_thesis=(
                        "The contradictory evidence resolves consistently enough to "
                        "support a directional operating thesis."
                    ),
                    status="unresolved",
                    supporting_drivers=self._driver_ids(drivers),
                    supporting_evidence=list(assessment.evidence_ids),
                    falsifiers=[],
                    verification_metrics=[
                        signal.metric
                        for signal in assessment.signals
                        if signal.metric
                    ],
                    resolution_conditions=[
                        "关键经营与现金信号在可比口径下形成一致方向",
                    ],
                    conviction_up_conditions=[
                        "正向经营信号持续且与现金转化相互验证",
                    ],
                    deterioration_conditions=[
                        "负向经营或现金信号扩大并得到后续可比证据确认",
                    ],
                    next_check_date=next_check,
                    confidence=0.5,
                )
            ]

        return [
            Thesis(
                thesis_id=f"{company_id}:fundamentals",
                company_id=company_id,
                title="Fundamentals improve",
                statement="Multiple comparable directional signals support improving operating fundamentals.",
                mechanism=(
                    "Revenue, margin, capital-efficiency or cash evidence points in a "
                    "consistent positive direction."
                ),
                anti_thesis=(
                    "The apparent improvement reverses or fails to convert into "
                    "sustainable cash returns."
                ),
                status="active",
                supporting_drivers=self._driver_ids(drivers),
                supporting_evidence=list(assessment.evidence_ids),
                falsifiers=[Falsifier(metric="ocf", operator="<", threshold=0)],
                verification_metrics=[
                    signal.metric
                    for signal in assessment.signals
                    if signal.metric
                ],
                next_check_date=next_check,
                confidence=0.65,
            )
        ]
