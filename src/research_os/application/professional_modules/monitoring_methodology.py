"""Focused professional research modules: monitoring methodology."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from research_os.application.command import ResearchRunCommand
from research_os.contracts.artifact_values import MethodologyDisclosure
from research_os.contracts.artifact_values import MonitoringPlan
from research_os.contracts.artifact_values import MonitoringPlanItem
from research_os.contracts.artifact_values import PriorRunReview
from research_os.contracts.artifact_values import PriorRunReviewItem
from research_os.contracts.artifacts import ArtifactWrite
from research_os.policies import builtin_policy_registry
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import METHODOLOGY_DISCLOSURE
from research_os.runtime.core_artifacts import MONITORING_PLAN
from research_os.runtime.core_artifacts import MONITORING_PRIOR_RUN_REVIEW
from research_os.runtime.core_artifacts import STRATEGY_RESOLUTION
from research_os.runtime.modules import ModuleResult
from research_os.runtime.modules import ModuleSpec
from research_os.runtime.state import ResearchStateView
from research_os.application.professional_modules._common import _lineage_refs


class MonitoringResearchModule:
    spec = ModuleSpec(
        module_id="core:professional-monitoring",
        module_version="2.0.1",
        requires=frozenset(),
        provides=frozenset((MONITORING_PLAN, MONITORING_PRIOR_RUN_REVIEW)),
        required_for_completion=False,
    )

    def __init__(self, command: ResearchRunCommand) -> None:
        self._input = command.monitoring

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        del context, state
        next_ts = (
            self._input.next_verification_event.due_ts
            if self._input.next_verification_event is not None
            else None
        )
        items = tuple(
            MonitoringPlanItem(
                item_key=rule.rule_key,
                metric_id=rule.metric_id,
                condition=f"{rule.operator} {rule.threshold}",
                next_check_ts=next_ts,
                evidence_refs=rule.evidence_refs,
                assumption_refs=rule.assumption_refs,
            )
            for rule in self._input.monitoring_rules
        )
        plan_refs = _lineage_refs(
            self._input.monitoring_rules,
            self._input.verification_calendar,
            self._input.next_verification_event,
        )
        plan = MonitoringPlan(
            domain_status="SUPPORTED" if items else "INSUFFICIENT_EVIDENCE",
            items=items,
            evidence_refs=plan_refs,
        )

        reviews: list[PriorRunReviewItem] = []
        for item in self._input.prior_run_reviews:
            error = (
                None
                if item.predicted_value is None or item.actual_value is None
                else Decimal(str(item.actual_value)) - Decimal(str(item.predicted_value))
            )
            review_status: Literal["HIT", "MISS", "UNKNOWN"]
            if error is None or item.tolerance is None:
                review_status = "UNKNOWN"
            else:
                tolerance = Decimal(str(item.tolerance))
                review_status = "HIT" if abs(error) <= tolerance else "MISS"
            reviews.append(
                PriorRunReviewItem(
                    item_key=item.item_key,
                    prior_statement=item.prior_statement,
                    status=review_status,
                    error=error,
                    evidence_refs=item.evidence_refs,
                    assumption_refs=item.assumption_refs,
                )
            )
        review_refs = _lineage_refs(self._input.prior_run_reviews)
        review = PriorRunReview(
            domain_status="SUPPORTED" if reviews else "INSUFFICIENT_EVIDENCE",
            items=tuple(reviews),
            scored_count=sum(item.status in {"HIT", "MISS"} for item in reviews),
            hit_count=sum(item.status == "HIT" for item in reviews),
            miss_count=sum(item.status == "MISS" for item in reviews),
            evidence_refs=review_refs,
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS" if items or reviews else "INSUFFICIENT_EVIDENCE",
            writes=(
                ArtifactWrite(
                    key=MONITORING_PLAN,
                    value=plan,
                    producer_id=self.spec.module_id,
                    evidence_refs=plan_refs,
                ),
                ArtifactWrite(
                    key=MONITORING_PRIOR_RUN_REVIEW,
                    value=review,
                    producer_id=self.spec.module_id,
                    evidence_refs=review_refs,
                ),
            ),
        )


class MethodologyDisclosureModule:
    spec = ModuleSpec(
        module_id="core:professional-methodology",
        module_version="2.0.1",
        requires=frozenset((STRATEGY_RESOLUTION,)),
        provides=frozenset((METHODOLOGY_DISCLOSURE,)),
        required_for_completion=False,
    )

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        del context
        strategy = state.require(STRATEGY_RESOLUTION)
        plugin_keys = tuple(
            sorted(
                item.plugin_id
                for item in (*strategy.industry_plugins, *strategy.methodology_plugins)
            )
        )
        policy_keys = tuple(
            item.policy_id for item in builtin_policy_registry().snapshot().policies
        )
        limitations = tuple(
            ": ".join(
                part
                for part in (
                    gap.gap_type,
                    gap.business_model,
                    gap.missing_capability,
                    gap.reason_code,
                    gap.reason,
                )
                if part
            )
            for gap in strategy.coverage_gaps
        )
        refs = strategy.evidence_refs
        value = MethodologyDisclosure(
            domain_status="SUPPORTED" if plugin_keys or limitations else "INSUFFICIENT_EVIDENCE",
            policy_keys=policy_keys,
            plugin_keys=plugin_keys,
            limitations=limitations,
            evidence_refs=refs,
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS" if plugin_keys else "INSUFFICIENT_EVIDENCE",
            writes=(
                ArtifactWrite(
                    key=METHODOLOGY_DISCLOSURE,
                    value=value,
                    producer_id=self.spec.module_id,
                    evidence_refs=refs,
                ),
            ),
        )
