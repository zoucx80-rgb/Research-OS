"""Focused professional research modules: expectation forecast peer."""

from __future__ import annotations

from typing import Literal

from collections import defaultdict
from decimal import Decimal
from research_os.application.command import ResearchRunCommand
from research_os.contracts.artifact_values import ConsensusDistribution
from research_os.contracts.artifact_values import ExpectationGap as ExpectationGapValue
from research_os.contracts.artifact_values import ExpectationQualityAssessment
from research_os.contracts.artifact_values import ExpectationSnapshot
from research_os.contracts.artifact_values import ForecastEvaluation
from research_os.contracts.artifact_values import NormalizedPeer
from research_os.contracts.artifact_values import NormalizedPeerSet
from research_os.contracts.artifacts import ArtifactWrite
from research_os.expectations.models import ConsensusVintage as DomainConsensusVintage
from research_os.expectations.validation import ExpectationEvidenceValidator
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import EXPECTATION_CONSENSUS_DISTRIBUTION
from research_os.runtime.core_artifacts import EXPECTATION_GAP
from research_os.runtime.core_artifacts import EXPECTATION_QUALITY
from research_os.runtime.core_artifacts import EXPECTATION_SNAPSHOT
from research_os.runtime.core_artifacts import FORECAST_EVALUATION
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
        provides=frozenset((FORECAST_EVALUATION,)),
        required_for_completion=False,
    )

    def __init__(self, command: ResearchRunCommand) -> None:
        self._input = command.forecasting

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        del context, state
        refs = _lineage_refs(self._input.hypotheses)
        value = ForecastEvaluation(
            domain_status="INSUFFICIENT_EVIDENCE",
            model_key=(
                self._input.hypotheses[0].hypothesis_key if self._input.hypotheses else None
            ),
            evaluation_status="INSUFFICIENT_EVIDENCE",
            evidence_refs=refs,
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status="INSUFFICIENT_EVIDENCE",
            diagnostics=("out-of-sample benchmark evidence is required",),
            writes=(
                ArtifactWrite(
                    key=FORECAST_EVALUATION,
                    value=value,
                    producer_id=self.spec.module_id,
                    evidence_refs=refs,
                ),
            ),
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
