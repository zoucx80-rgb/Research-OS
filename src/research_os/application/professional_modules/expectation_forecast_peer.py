"""Focused professional research modules: expectation forecast peer."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from collections import defaultdict
from decimal import Decimal
from research_os.application.command import ResearchRunCommand
from research_os.contracts.artifact_values import ConsensusDistribution
from research_os.contracts.artifact_values import ExpectationGap as ExpectationGapValue
from research_os.contracts.artifact_values import ExpectationQualityAssessment
from research_os.contracts.artifact_values import ExpectationSnapshot
from research_os.contracts.artifact_values import ForecastEvaluation
from research_os.contracts.artifact_values import ForecastFoldEvaluation
from research_os.contracts.artifact_values import NormalizedPeer
from research_os.contracts.artifact_values import NormalizedPeerSet
from research_os.contracts.artifacts import ArtifactWrite
from research_os.contracts.evidence import EvidenceRef
from research_os.expectations.models import ConsensusVintage as DomainConsensusVintage
from research_os.expectations.validation import ExpectationEvidenceValidator
from research_os.forecasting.backtest import BacktestResult
from research_os.forecasting.benchmarks import BenchmarkRegistry
from research_os.forecasting.benchmarks import builtin_benchmark_registry
from research_os.forecasting.contracts import ForecastBenchmarkEvidence
from research_os.forecasting.contracts import ForecastMetricEvidence
from research_os.forecasting.contracts import ForecastStabilityEvidence
from research_os.forecasting.experiment import ForecastExperimentValidator
from research_os.forecasting.promotion import decide_promotion
from research_os.forecasting.backtest import TimeSeriesBacktester
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import EXPECTATION_CONSENSUS_DISTRIBUTION
from research_os.runtime.core_artifacts import EXPECTATION_GAP
from research_os.runtime.core_artifacts import EXPECTATION_QUALITY
from research_os.runtime.core_artifacts import EXPECTATION_SNAPSHOT
from research_os.runtime.core_artifacts import FORECAST_EVALUATION
from research_os.runtime.core_artifacts import FORECAST_BENCHMARK_EVIDENCE
from research_os.runtime.core_artifacts import PEERS_NORMALIZED
from research_os.runtime.modules import ModuleResult
from research_os.runtime.modules import ModuleSpec
from research_os.runtime.modules import ModuleStatus
from research_os.runtime.state import ResearchStateView
from statistics import median
from research_os.application.professional_modules._common import _lineage_refs


class ExpectationResearchModule:
    spec = ModuleSpec(
        module_id="core:professional-expectation",
        module_version="2.0.1",
        requires=frozenset(),
        provides=frozenset(
            (
                EXPECTATION_SNAPSHOT,
                EXPECTATION_QUALITY,
                EXPECTATION_GAP,
                EXPECTATION_CONSENSUS_DISTRIBUTION,
            )
        ),
        required_for_completion=False,
    )

    def __init__(self, command: ResearchRunCommand) -> None:
        self._input = command.expectations
        self._validator = ExpectationEvidenceValidator()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        del state
        vintage = self._input.vintage
        vintage_refs = _lineage_refs(vintage)
        snapshot = ExpectationSnapshot(
            domain_status="SUPPORTED" if vintage is not None else "INSUFFICIENT_EVIDENCE",
            company_id=context.company.company_id if vintage is not None else None,
            decision_ts=context.decision_ts if vintage is not None else None,
            vintage=vintage,
            evidence_refs=vintage_refs,
        )
        domain_vintage = (
            None
            if vintage is None
            else DomainConsensusVintage.model_validate(
                vintage.model_dump(exclude={"evidence_refs", "assumption_refs"})
            )
        )
        quality_result = self._validator.assess_consensus_quality(
            vintage=domain_vintage,
            decision_ts=context.decision_ts,
            latest_material_event_ts=self._input.latest_material_event_ts,
        )
        quality = ExpectationQualityAssessment(
            domain_status=(
                "SUPPORTED" if quality_result.status != "UNKNOWN" else "INSUFFICIENT_EVIDENCE"
            ),
            quality_status=quality_result.status,
            reason_codes=tuple(quality_result.reason_codes),
            age_days=quality_result.age_days,
            source_count=quality_result.source_count,
            evidence_refs=vintage_refs,
        )
        gap = self._input.gap or ExpectationGapValue()
        gap_refs = _lineage_refs(gap)

        observations = self._input.consensus_observations
        observation_refs = _lineage_refs(observations)
        metric_ids = {item.metric_id for item in observations}
        periods = {item.forecast_period for item in observations}
        values = [float(item.value) for item in observations]
        comparable = bool(observations) and len(metric_ids) == 1 and len(periods) == 1
        distribution = ConsensusDistribution(
            domain_status="SUPPORTED" if comparable else "INSUFFICIENT_EVIDENCE",
            metric_id=next(iter(metric_ids)) if len(metric_ids) == 1 else None,
            forecast_period=next(iter(periods)) if len(periods) == 1 else None,
            observations=observations,
            source_count=len(observations),
            low=min(values) if comparable else None,
            median=median(values) if comparable else None,
            high=max(values) if comparable else None,
            evidence_refs=observation_refs,
        )
        refs = _lineage_refs(vintage_refs, gap_refs, observation_refs)
        status: ModuleStatus = "PASS" if refs else "INSUFFICIENT_EVIDENCE"
        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            writes=(
                ArtifactWrite(
                    key=EXPECTATION_SNAPSHOT,
                    value=snapshot,
                    producer_id=self.spec.module_id,
                    evidence_refs=vintage_refs,
                ),
                ArtifactWrite(
                    key=EXPECTATION_QUALITY,
                    value=quality,
                    producer_id=self.spec.module_id,
                    evidence_refs=vintage_refs,
                ),
                ArtifactWrite(
                    key=EXPECTATION_GAP,
                    value=gap,
                    producer_id=self.spec.module_id,
                    evidence_refs=gap_refs,
                ),
                ArtifactWrite(
                    key=EXPECTATION_CONSENSUS_DISTRIBUTION,
                    value=distribution,
                    producer_id=self.spec.module_id,
                    evidence_refs=observation_refs,
                ),
            ),
        )


class ForecastResearchModule:
    spec = ModuleSpec(
        module_id="core:professional-forecast",
        module_version="2.0.1",
        requires=frozenset(),
        provides=frozenset((FORECAST_EVALUATION, FORECAST_BENCHMARK_EVIDENCE)),
        required_for_completion=False,
    )

    def __init__(
        self,
        command: ResearchRunCommand,
        *,
        benchmark_registry: BenchmarkRegistry | None = None,
    ) -> None:
        self._input = command.forecasting
        self._benchmarks = benchmark_registry or builtin_benchmark_registry()
        self._validator = ForecastExperimentValidator(self._benchmarks)
        self._backtester = TimeSeriesBacktester(self._benchmarks)

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        del state
        experiment = self._input.experiment
        refs = _lineage_refs(self._input.hypotheses, experiment)
        if experiment is None:
            return self._insufficient(
                reason_codes=("EXPERIMENT_NOT_PROVIDED",),
                evidence_refs=refs,
            )

        registered_hypotheses = {
            hypothesis.hypothesis_key for hypothesis in self._input.hypotheses
        }
        assessment = self._validator.assess(
            experiment,
            registered_hypotheses=registered_hypotheses,
            decision_ts=context.decision_ts,
        )
        if assessment.status == "INSUFFICIENT_EVIDENCE":
            return self._insufficient(
                reason_codes=assessment.reason_codes,
                evidence_refs=refs,
                model_key=experiment.model_key,
                benchmark_key=experiment.benchmark_id,
                evaluation_ts=experiment.evaluation_ts,
            )

        result = self._backtester.run(
            observations=experiment.observations,
            feature_names=experiment.feature_names,
            target=experiment.target_metric,
            benchmark_id=experiment.benchmark_id,
            evaluation_ts=experiment.evaluation_ts,
            n_splits=experiment.n_splits,
        )
        promotion = decide_promotion(
            current_stage=experiment.current_model_stage,
            evaluation=result,
            benchmark_registry=self._benchmarks,
            hypothesis_registered=experiment.hypothesis_key in registered_hypotheses,
        )
        evaluation = ForecastEvaluation(
            domain_status="SUPPORTED",
            model_key=experiment.model_key,
            benchmark_key=result.benchmark_id,
            evaluation_status=(
                "PASS" if promotion.reason == "all promotion gates passed" else "FAIL"
            ),
            train_cutoff=result.train_cutoff,
            evaluation_ts=result.evaluation_ts,
            folds=self._fold_evaluations(result),
            evidence_refs=refs,
        )
        evidence = ForecastBenchmarkEvidence(
            domain_status="SUPPORTED",
            model_key=experiment.model_key,
            target_metric=experiment.target_metric,
            horizon=experiment.horizon,
            benchmark_key=result.benchmark_id,
            benchmark_version=result.benchmark_version,
            sample_count=len(experiment.observations),
            fold_count=len(result.folds),
            out_of_sample=result.out_of_sample,
            pit_compliant=result.pit_compliant,
            metrics=tuple(
                ForecastMetricEvidence(
                    metric_name=metric.name,
                    value=Decimal(str(metric.value)),
                    evidence_refs=metric.evidence_refs,
                )
                for metric in result.metrics
            ),
            benchmark_mae=Decimal(str(result.benchmark_mae)),
            improvement=(
                None
                if result.benchmark_improvement is None
                else Decimal(str(result.benchmark_improvement))
            ),
            stability_windows=tuple(
                ForecastStabilityEvidence(
                    window_key=window.window_id,
                    model_mae=Decimal(str(window.model_mae)),
                    benchmark_mae=Decimal(str(window.benchmark_mae)),
                    evidence_refs=window.evidence_refs,
                )
                for window in result.stability_windows
            ),
            stable=result.stable,
            current_stage=promotion.current_stage,
            next_stage=promotion.next_stage,
            promotion_reason=promotion.reason,
            applicability=experiment.applicability,
            model_boundary=experiment.model_boundary,
            caveats=experiment.caveats,
            evidence_refs=refs,
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS",
            diagnostics=(promotion.reason,),
            writes=(
                ArtifactWrite(
                    key=FORECAST_EVALUATION,
                    value=evaluation,
                    producer_id=self.spec.module_id,
                    evidence_refs=refs,
                ),
                ArtifactWrite(
                    key=FORECAST_BENCHMARK_EVIDENCE,
                    value=evidence,
                    producer_id=self.spec.module_id,
                    evidence_refs=refs,
                ),
            ),
        )

    def _insufficient(
        self,
        *,
        reason_codes: tuple[str, ...],
        evidence_refs: tuple[EvidenceRef, ...],
        model_key: str | None = None,
        benchmark_key: str | None = None,
        evaluation_ts: datetime | None = None,
    ) -> ModuleResult:
        evaluation = ForecastEvaluation(
            domain_status="INSUFFICIENT_EVIDENCE",
            model_key=model_key,
            benchmark_key=benchmark_key,
            evaluation_status="INSUFFICIENT_EVIDENCE",
            evaluation_ts=evaluation_ts,
            reason_codes=reason_codes,
            evidence_refs=evidence_refs,
        )
        evidence = ForecastBenchmarkEvidence(
            domain_status="INSUFFICIENT_EVIDENCE",
            model_key=model_key,
            benchmark_key=benchmark_key,
            reason_codes=reason_codes,
            evidence_refs=evidence_refs,
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status="INSUFFICIENT_EVIDENCE",
            diagnostics=reason_codes,
            writes=(
                ArtifactWrite(
                    key=FORECAST_EVALUATION,
                    value=evaluation,
                    producer_id=self.spec.module_id,
                    evidence_refs=evidence_refs,
                ),
                ArtifactWrite(
                    key=FORECAST_BENCHMARK_EVIDENCE,
                    value=evidence,
                    producer_id=self.spec.module_id,
                    evidence_refs=evidence_refs,
                ),
            ),
        )

    @staticmethod
    def _fold_evaluations(result: BacktestResult) -> tuple[ForecastFoldEvaluation, ...]:
        windows = {window.window_id: window for window in result.stability_windows}
        return tuple(
            ForecastFoldEvaluation(
                fold_key=fold.fold_id,
                feature_available_ts=max(
                    timestamp
                    for item in (*fold.train_observations, *fold.test_observations)
                    for timestamp in item.feature_available_ts.values()
                ),
                label_mature_ts=max(
                    item.label_mature_ts
                    for item in (*fold.train_observations, *fold.test_observations)
                ),
                evaluation_ts=fold.evaluation_ts,
                model_error=Decimal(str(windows[fold.fold_id].model_mae)),
                benchmark_error=Decimal(str(windows[fold.fold_id].benchmark_mae)),
            )
            for fold in result.folds
        )


class PeerResearchModule:
    spec = ModuleSpec(
        module_id="core:professional-peers",
        module_version="2.0.1",
        requires=frozenset(),
        provides=frozenset((PEERS_NORMALIZED,)),
        required_for_completion=False,
    )

    def __init__(self, command: ResearchRunCommand) -> None:
        self._input = command.peers

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        del context, state
        observations = self._input.peer_comparables
        refs = _lineage_refs(observations)
        basis_by_metric: dict[str, set[tuple[str, str | None, str | None]]] = defaultdict(set)
        for item in observations:
            basis_by_metric[item.metric_id].add((item.period, item.unit, item.accounting_scope))
        peers: list[NormalizedPeer] = []
        for item in observations:
            bases = basis_by_metric[item.metric_id]
            peer_status: Literal[
                "COMPARABLE", "ADJUSTMENT_REQUIRED", "NOT_COMPARABLE", "INSUFFICIENT_EVIDENCE"
            ]
            reasons: tuple[str, ...]
            if item.value is None:
                peer_status = "INSUFFICIENT_EVIDENCE"
                reasons = ("MISSING_VALUE",)
            elif None in (item.unit, item.accounting_scope) or len(bases) != 1:
                peer_status = "NOT_COMPARABLE"
                reasons = ("COMPARISON_BASIS_MISMATCH",)
            else:
                peer_status = "COMPARABLE"
                reasons = ()
            peers.append(
                NormalizedPeer(
                    company_id=item.peer_key,
                    metric_id=item.metric_id,
                    status=peer_status,
                    value=Decimal(str(item.value)) if item.value is not None else None,
                    unit=item.unit,
                    period=item.period,
                    reason_codes=reasons,
                    evidence_refs=item.evidence_refs,
                    assumption_refs=item.assumption_refs,
                )
            )
        substantive = any(item.status == "COMPARABLE" for item in peers)
        value = NormalizedPeerSet(
            domain_status="SUPPORTED" if substantive else "INSUFFICIENT_EVIDENCE",
            peers=tuple(peers),
            evidence_refs=refs,
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS" if substantive else "INSUFFICIENT_EVIDENCE",
            writes=(
                ArtifactWrite(
                    key=PEERS_NORMALIZED,
                    value=value,
                    producer_id=self.spec.module_id,
                    evidence_refs=refs,
                ),
            ),
        )
