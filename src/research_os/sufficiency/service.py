from __future__ import annotations

from collections.abc import Iterable

from research_os.contracts.artifact_values import DomainStatus
from research_os.contracts.evidence import EvidenceRef
from research_os.forecasting.contracts import ForecastBenchmarkEvidence
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
_FORECAST_DOMAIN = "forecast"
_FORECAST_METRICS = frozenset(
    ("MAE", "RMSE", "DIRECTION_ACCURACY", "INTERVAL_COVERAGE")
)


class ResearchSufficiencyEvaluator:
    """Evaluate whether canonical artifacts substantively support research conclusions."""

    def evaluate(self, state: ResearchStateView) -> ResearchSufficiencyAssessment:
        from research_os.runtime.core_artifacts import (
            FINANCIAL_TEMPORAL_ANALYSIS,
            FORECAST_BENCHMARK_EVIDENCE,
        )

        temporal = state.get(FINANCIAL_TEMPORAL_ANALYSIS)
        forecast = state.get(FORECAST_BENCHMARK_EVIDENCE)
        domains: tuple[DomainSufficiencyAssessment, ...] = (
            self._financial_temporal(temporal),
        )
        if forecast is not None:
            domains = (*domains, self._forecast(forecast))
        blocking_gap_keys = tuple(
            gap.gap_key for domain in domains for gap in domain.material_gaps
        )
        if (
            all(domain.coverage == "COMPLETE" for domain in domains)
            and all(domain.evidence_quality == "COMPLETE" for domain in domains)
            and not blocking_gap_keys
        ):
            overall_status: SufficiencyStatus = "SUFFICIENT"
            domain_status: DomainStatus = "SUPPORTED"
        elif (
            not blocking_gap_keys
            and all(domain.coverage in {"COMPLETE", "PARTIAL"} for domain in domains)
            and all(domain.evidence_quality != "MISSING" for domain in domains)
        ):
            overall_status = "LIMITED"
            domain_status = "SUPPORTED"
        else:
            overall_status = "INSUFFICIENT_EVIDENCE"
            domain_status = "INSUFFICIENT_EVIDENCE"
        return ResearchSufficiencyAssessment(
            domain_status=domain_status,
            overall_status=overall_status,
            domains=domains,
            blocking_gap_keys=blocking_gap_keys,
            evidence_refs=self._unique_refs(
                reference for domain in domains for reference in domain.evidence_refs
            ),
            assumption_refs=tuple(
                {
                    (
                        reference.assumption_key,
                        reference.assumption_version,
                        reference.content_fingerprint,
                    ): reference
                    for domain in domains
                    for reference in domain.assumption_refs
                }.values()
            ),
        )

    @staticmethod
    def _unique_refs(references: Iterable[EvidenceRef]) -> tuple[EvidenceRef, ...]:
        return tuple(
            {
                (item.evidence_id, item.revision, item.content_fingerprint): item
                for item in references
            }.values()
        )

    @staticmethod
    def _forecast(forecast: ForecastBenchmarkEvidence) -> DomainSufficiencyAssessment:
        metric_names = {item.metric_name for item in forecast.metrics}
        benchmark_complete = bool(
            forecast.out_of_sample
            and forecast.benchmark_key
            and forecast.benchmark_version
            and forecast.fold_count > 0
        )
        executable = bool(
            forecast.domain_status == "SUPPORTED"
            and benchmark_complete
            and forecast.pit_compliant
            and metric_names == _FORECAST_METRICS
            and forecast.sample_count >= forecast.fold_count + 2
            and forecast.stability_windows
        )
        derived_reasons: list[str] = list(forecast.reason_codes)
        if not forecast.out_of_sample:
            derived_reasons.append("OOS_BENCHMARK_MISSING")
        if not (forecast.benchmark_key and forecast.benchmark_version):
            derived_reasons.append("REGISTERED_BENCHMARK_MISSING")
        if not forecast.pit_compliant:
            derived_reasons.append("PIT_COMPLIANCE_FAILED")
        if metric_names != _FORECAST_METRICS:
            derived_reasons.append("FORECAST_METRICS_INCOMPLETE")
        if not forecast.stability_windows:
            derived_reasons.append("STABILITY_EVIDENCE_MISSING")
        reasons = tuple(sorted(set(derived_reasons)))
        gaps = tuple(
            MaterialResearchGap(
                gap_key=f"{_FORECAST_DOMAIN}:{reason}",
                domain_id=_FORECAST_DOMAIN,
                reason_code=reason,
                description=f"Forecast benchmark evidence is incomplete: {reason}.",
                required_evidence=(
                    "PIT-safe out-of-sample evaluation against a registered benchmark",
                    "complete canonical forecast metrics and stability windows",
                ),
                evidence_refs=forecast.evidence_refs,
                assumption_refs=forecast.assumption_refs,
            )
            for reason in reasons
        )
        if forecast.evidence_refs:
            evidence_quality: CoverageLevel = "COMPLETE"
        elif forecast.assumption_refs:
            evidence_quality = "PARTIAL"
        else:
            evidence_quality = "MISSING"
        known_items = tuple(
            sorted(
                {
                    *(f"metric:{name}" for name in metric_names),
                    *(
                        (f"benchmark:{forecast.benchmark_key}",)
                        if forecast.benchmark_key
                        else ()
                    ),
                    *((f"model:{forecast.model_key}",) if forecast.model_key else ()),
                }
            )
        )
        return DomainSufficiencyAssessment(
            domain_id=_FORECAST_DOMAIN,
            coverage="COMPLETE" if executable else ("PARTIAL" if known_items else "MISSING"),
            evidence_quality=evidence_quality,
            temporal_coverage="NOT_APPLICABLE",
            benchmark_coverage="COMPLETE" if benchmark_complete else "MISSING",
            peer_coverage="NOT_APPLICABLE",
            model_executability="EXECUTABLE" if executable else "BLOCKED",
            known_items=known_items,
            unknown_items=tuple(f"forecast_evidence:{reason}" for reason in reasons),
            why_unknown=reasons,
            upgrade_evidence_requirements=(
                ()
                if not reasons
                else (
                    "add a PIT-safe OOS experiment with a registered benchmark, canonical metrics, and stability evidence",
                )
            ),
            material_gaps=gaps,
            evidence_refs=forecast.evidence_refs,
            assumption_refs=forecast.assumption_refs,
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
