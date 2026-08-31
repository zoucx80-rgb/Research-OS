from __future__ import annotations

from research_os.completeness import (
    build_cash_flow_quality_bridge,
    build_consensus_distribution,
    build_prior_run_review,
)
from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.modules import ModuleResult, ModuleSpec


class ResearchCompletenessModule:
    """Project explicit professional-research inputs into canonical artifacts."""

    spec = ModuleSpec(
        module_id="research_completeness",
        module_version="1.0.0",
        requires=frozenset({"evidence.pit"}),
        provides=frozenset(
            {
                "research.operating_evidence",
                "financial.time_series",
                "cash_flow.quality_bridge",
                "expectation.consensus_distribution",
                "peers.comparables",
                "scenario.sensitivities",
                "monitoring.rules",
                "monitoring.verification_calendar",
                "monitoring.prior_run_review",
                "methodology.disclosure",
            }
        ),
        required_for_completion=False,
    )

    def __init__(self, *, inputs: ResearchInputs | None = None):
        self.inputs = inputs or ResearchInputs()

    @staticmethod
    def _methodology_disclosure() -> dict[str, str]:
        return {
            "architecture": "canonical runtime -> human-readable view -> report document -> Markdown -> HTML -> PDF",
            "pit_rule": "publish_ts <= decision_ts",
            "lineage_rule": "facts, calculations, statistical evidence and assumptions retain distinct provenance",
            "threshold_policy": "monitoring thresholds are explicit inputs, not universal constants",
            "cash_flow_methodology": "simplified FCF is operating cash flow minus capex cash when both are supplied; simplified FCF is not FCFF",
            "missingness_policy": "missing research inputs remain missing and may produce incomplete research-depth coverage",
        }

    @staticmethod
    def _evidence_ids(items) -> list[str]:
        ids: list[str] = []
        for item in items:
            ids.extend(getattr(item, "evidence_ids", ()) or ())
        return ids

    def run(self, context, state) -> ModuleResult:
        artifacts: dict[str, object] = {
            "methodology.disclosure": self._methodology_disclosure(),
        }
        evidence_ids: list[str] = []

        if self.inputs.operating_observations:
            artifacts["research.operating_evidence"] = self.inputs.operating_observations
            evidence_ids.extend(self._evidence_ids(self.inputs.operating_observations))

        if self.inputs.financial_time_series:
            artifacts["financial.time_series"] = self.inputs.financial_time_series
            for series in self.inputs.financial_time_series:
                evidence_ids.extend(self._evidence_ids(series.points))

        if self.inputs.cash_flow_quality_input is not None:
            bridge = build_cash_flow_quality_bridge(self.inputs.cash_flow_quality_input)
            artifacts["cash_flow.quality_bridge"] = bridge
            evidence_ids.extend(bridge.evidence_ids)

        if self.inputs.consensus_observations:
            keys = sorted(
                {
                    (item.metric, item.forecast_period)
                    for item in self.inputs.consensus_observations
                }
            )
            distributions = tuple(
                build_consensus_distribution(
                    observations=self.inputs.consensus_observations,
                    decision_ts=context.decision_ts,
                    metric=metric,
                    forecast_period=forecast_period,
                )
                for metric, forecast_period in keys
            )
            artifacts["expectation.consensus_distribution"] = distributions
            for item in distributions:
                evidence_ids.extend(item.evidence_ids)

        if self.inputs.peer_comparables:
            artifacts["peers.comparables"] = self.inputs.peer_comparables
            evidence_ids.extend(self._evidence_ids(self.inputs.peer_comparables))

        if self.inputs.sensitivities:
            artifacts["scenario.sensitivities"] = self.inputs.sensitivities
            evidence_ids.extend(self._evidence_ids(self.inputs.sensitivities))

        if self.inputs.monitoring_rules:
            artifacts["monitoring.rules"] = self.inputs.monitoring_rules
            evidence_ids.extend(self._evidence_ids(self.inputs.monitoring_rules))

        if self.inputs.verification_calendar:
            artifacts["monitoring.verification_calendar"] = self.inputs.verification_calendar
            evidence_ids.extend(self._evidence_ids(self.inputs.verification_calendar))

        if self.inputs.prior_run_review_items:
            review = build_prior_run_review(items=self.inputs.prior_run_review_items)
            artifacts["monitoring.prior_run_review"] = review
            for item in review.items:
                evidence_ids.extend(item.evidence_ids)

        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS",
            artifacts=artifacts,
            evidence_ids=list(dict.fromkeys(item for item in evidence_ids if item)),
        )
