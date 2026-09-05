from __future__ import annotations

from research_os.contracts.artifact_values import DomainStatus
from research_os.runtime.state import ResearchStateView
from research_os.sufficiency.models import (
    CoverageLevel,
    DomainSufficiencyAssessment,
    MaterialResearchGap,
    ResearchSufficiencyAssessment,
    SufficiencyStatus,
)
from research_os.temporal.models import FinancialTemporalAnalysis


_FINANCIAL_TEMPORAL_DOMAIN = "financial_temporal"


class ResearchSufficiencyEvaluator:
    """Evaluate whether canonical artifacts substantively support research conclusions."""

    def evaluate(self, state: ResearchStateView) -> ResearchSufficiencyAssessment:
        from research_os.runtime.core_artifacts import FINANCIAL_TEMPORAL_ANALYSIS

        temporal = state.get(FINANCIAL_TEMPORAL_ANALYSIS)
        domain = self._financial_temporal(temporal)
        blocking_gap_keys = tuple(gap.gap_key for gap in domain.material_gaps)
        if (
            domain.temporal_coverage == "COMPLETE"
            and domain.evidence_quality == "COMPLETE"
            and not blocking_gap_keys
        ):
            overall_status: SufficiencyStatus = "SUFFICIENT"
            domain_status: DomainStatus = "SUPPORTED"
        elif (
            domain.temporal_coverage in {"COMPLETE", "PARTIAL"}
            and domain.evidence_quality != "MISSING"
        ):
            overall_status = "LIMITED"
            domain_status = "SUPPORTED"
        else:
            overall_status = "INSUFFICIENT_EVIDENCE"
            domain_status = "INSUFFICIENT_EVIDENCE"
        return ResearchSufficiencyAssessment(
            domain_status=domain_status,
            overall_status=overall_status,
            domains=(domain,),
            blocking_gap_keys=blocking_gap_keys,
            evidence_refs=domain.evidence_refs,
            assumption_refs=domain.assumption_refs,
        )

    @staticmethod
    def _financial_temporal(
        temporal: FinancialTemporalAnalysis | None,
    ) -> DomainSufficiencyAssessment:
        if temporal is None:
            reason = "FINANCIAL_TEMPORAL_ANALYSIS_MISSING"
            gap = MaterialResearchGap(
                gap_key=f"{_FINANCIAL_TEMPORAL_DOMAIN}:{reason}",
                domain_id=_FINANCIAL_TEMPORAL_DOMAIN,
                reason_code=reason,
                description="Financial temporal analysis artifact is missing.",
                required_evidence=(
                    "at least two comparable financial periods",
                    "explicit comparison basis",
                    "revision-bound lineage",
                ),
            )
            return DomainSufficiencyAssessment(
                domain_id=_FINANCIAL_TEMPORAL_DOMAIN,
                coverage="MISSING",
                evidence_quality="MISSING",
                temporal_coverage="MISSING",
                benchmark_coverage="NOT_APPLICABLE",
                peer_coverage="NOT_APPLICABLE",
                model_executability="NOT_APPLICABLE",
                known_items=(),
                unknown_items=("comparable_financial_trends",),
                why_unknown=(reason,),
                upgrade_evidence_requirements=(
                    "add comparable period observations with explicit basis and lineage",
                ),
                material_gaps=(gap,),
            )

        observed_metrics = tuple(sorted({item.metric_id for item in temporal.observations}))
        comparable_metrics = tuple(
            sorted(
                {
                    item.metric_id
                    for item in temporal.assessments
                    if item.comparison_status == "PASS"
                }
            )
        )
        unresolved_metrics = tuple(
            sorted(
                {
                    item.metric_id
                    for item in temporal.assessments
                    if item.comparison_status != "PASS"
                }
            )
        )
        known_items = tuple(
            sorted(
                {
                    *(f"observation:{metric_id}" for metric_id in observed_metrics),
                    *(f"comparable_trend:{metric_id}" for metric_id in comparable_metrics),
                }
            )
        )
        unknown_items = tuple(f"comparable_trend:{metric_id}" for metric_id in unresolved_metrics)
        upgrade_requirements = tuple(
            f"add a comparable {metric_id} period with explicit basis and revision-bound lineage"
            for metric_id in unresolved_metrics
        )
        gaps = tuple(
            ResearchSufficiencyEvaluator._temporal_gap(temporal, unresolved_gap)
            for unresolved_gap in temporal.unresolved_gaps
        )
        why_unknown = temporal.unresolved_gaps
        if not temporal.observations:
            observation_reason = "TEMPORAL_OBSERVATIONS_MISSING"
            unknown_items = (*unknown_items, "comparable_financial_trends")
            why_unknown = (*why_unknown, observation_reason)
            upgrade_requirements = (
                *upgrade_requirements,
                "add at least two comparable financial periods with explicit basis and lineage",
            )
            gaps = (
                *gaps,
                MaterialResearchGap(
                    gap_key=f"{_FINANCIAL_TEMPORAL_DOMAIN}:{observation_reason}",
                    domain_id=_FINANCIAL_TEMPORAL_DOMAIN,
                    reason_code=observation_reason,
                    description="Financial period observations are missing.",
                    required_evidence=(
                        "at least two comparable financial periods",
                        "explicit comparison basis",
                        "revision-bound lineage",
                    ),
                ),
            )

        if temporal.temporal_coverage == "SUFFICIENT":
            coverage: CoverageLevel = "COMPLETE"
            temporal_coverage: CoverageLevel = "COMPLETE"
        elif temporal.temporal_coverage == "LIMITED":
            coverage = "PARTIAL"
            temporal_coverage = "PARTIAL"
        else:
            coverage = "PARTIAL" if temporal.observations else "MISSING"
            temporal_coverage = "MISSING"
        if temporal.evidence_refs:
            evidence_quality: CoverageLevel = "COMPLETE"
        elif temporal.assumption_refs:
            evidence_quality = "PARTIAL"
        else:
            evidence_quality = "MISSING"
        lineage_present = evidence_quality != "MISSING"
        if not lineage_present:
            lineage_reason = "LINEAGE_MISSING"
            unknown_items = (*unknown_items, "lineage:financial_temporal")
            why_unknown = (*why_unknown, lineage_reason)
            upgrade_requirements = (
                *upgrade_requirements,
                "add revision-bound evidence or assumption lineage",
            )
            gaps = (
                *gaps,
                MaterialResearchGap(
                    gap_key=f"{_FINANCIAL_TEMPORAL_DOMAIN}:{lineage_reason}",
                    domain_id=_FINANCIAL_TEMPORAL_DOMAIN,
                    reason_code=lineage_reason,
                    description="Financial temporal conclusions have no bound lineage.",
                    required_evidence=("revision-bound evidence or assumption lineage",),
                ),
            )
        return DomainSufficiencyAssessment(
            domain_id=_FINANCIAL_TEMPORAL_DOMAIN,
            coverage=coverage,
            evidence_quality=evidence_quality,
            temporal_coverage=temporal_coverage,
            benchmark_coverage="NOT_APPLICABLE",
            peer_coverage="NOT_APPLICABLE",
            model_executability="NOT_APPLICABLE",
            known_items=known_items,
            unknown_items=unknown_items,
            why_unknown=why_unknown,
            upgrade_evidence_requirements=upgrade_requirements,
            material_gaps=gaps,
            evidence_refs=temporal.evidence_refs,
            assumption_refs=temporal.assumption_refs,
        )

    @staticmethod
    def _temporal_gap(
        temporal: FinancialTemporalAnalysis,
        unresolved_gap: str,
    ) -> MaterialResearchGap:
        metric_id, _, reason_code = unresolved_gap.partition(":")
        normalized_reason = reason_code or "TEMPORAL_COMPARISON_UNRESOLVED"
        return MaterialResearchGap(
            gap_key=f"{_FINANCIAL_TEMPORAL_DOMAIN}:{metric_id}:{normalized_reason}",
            domain_id=_FINANCIAL_TEMPORAL_DOMAIN,
            reason_code=normalized_reason,
            description=f"Comparable temporal evidence for {metric_id} is unresolved.",
            required_evidence=(
                f"comparable {metric_id} period",
                "explicit comparison basis",
                "revision-bound lineage",
            ),
            evidence_refs=temporal.evidence_refs,
            assumption_refs=temporal.assumption_refs,
        )
