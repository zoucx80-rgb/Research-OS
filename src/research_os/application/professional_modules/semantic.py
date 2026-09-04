"""Focused professional research modules: semantic."""

from __future__ import annotations

from research_os.application.command import ResearchRunCommand
from research_os.contracts.artifact_values import DirectionalSignal
from research_os.contracts.artifact_values import DriverGraph
from research_os.contracts.artifact_values import DriverNode
from research_os.contracts.artifact_values import SemanticClaim
from research_os.contracts.artifact_values import SemanticClaims
from research_os.contracts.artifact_values import SemanticSignalAssessment
from research_os.contracts.artifacts import ArtifactWrite
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import DRIVERS_GRAPH
from research_os.runtime.core_artifacts import SEMANTIC_CLAIMS
from research_os.runtime.core_artifacts import THESIS_PORTFOLIO
from research_os.runtime.core_artifacts import THESIS_SEMANTIC_SIGNAL_ASSESSMENT
from research_os.runtime.modules import ModuleResult
from research_os.runtime.modules import ModuleSpec
from research_os.runtime.modules import ModuleStatus
from research_os.runtime.state import ResearchStateView
from research_os.application.professional_modules._common import _lineage_refs


class DriverSemanticResearchModule:
    spec = ModuleSpec(
        module_id="core:professional-thesis-semantics",
        module_version="2.0.1",
        requires=frozenset((THESIS_PORTFOLIO,)),
        provides=frozenset((DRIVERS_GRAPH, THESIS_SEMANTIC_SIGNAL_ASSESSMENT, SEMANTIC_CLAIMS)),
        required_for_completion=False,
    )

    def __init__(self, command: ResearchRunCommand) -> None:
        self._input = command.thesis

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        portfolio = state.require(THESIS_PORTFOLIO)
        refs = _lineage_refs(self._input, portfolio)
        driver_keys: set[str] = set()
        for thesis in (
            *((portfolio.primary,) if portfolio.primary is not None else ()),
            *portfolio.supporting,
            *portfolio.conflicting,
            *portfolio.unresolved,
            *portfolio.falsified,
        ):
            driver_keys.update(thesis.supporting_driver_keys)
        for rule in self._input.comparison_rules:
            driver_keys.update((rule.left_metric, rule.right_metric))
        graph = DriverGraph(
            domain_status="SUPPORTED" if driver_keys else "INSUFFICIENT_EVIDENCE",
            company_id=context.company.company_id,
            nodes=tuple(
                DriverNode(
                    driver_key=key,
                    name=key,
                    driver_type="research_driver",
                    observable_metric=key,
                    evidence_refs=refs,
                )
                for key in sorted(driver_keys)
            ),
            evidence_refs=refs,
        )

        signals: list[DirectionalSignal] = []
        if self._input.cycle_recovery_observed is not None:
            support = self._input.cycle_turning_point_support
            supported = support is not None and support.status == "SUPPORTED"
            label = (
                "RECOVERY_NOT_OBSERVED"
                if not self._input.cycle_recovery_observed
                else "RECOVERY_OBSERVED_TROUGH_UNCONFIRMED"
                if supported
                else "RECOVERY_OBSERVED"
            )
            signals.append(
                DirectionalSignal(
                    metric_id="cycle_recovery",
                    direction="NEGATIVE" if not self._input.cycle_recovery_observed else "POSITIVE",
                    semantic_label=label,
                    evidence_refs=_lineage_refs(support),
                )
            )
        if self._input.moat_evidence:
            # ResearchAssertion does not encode barrier/economic-outcome type. Fail closed:
            # evidence can support a barrier statement, never realized economic moat.
            signals.append(
                DirectionalSignal(
                    metric_id="economic_moat",
                    direction="NEUTRAL",
                    semantic_label="BARRIER_EVIDENCE_PRESENT_ECONOMIC_MOAT_UNCONFIRMED",
                    evidence_refs=_lineage_refs(self._input.moat_evidence),
                )
            )
        assessment = SemanticSignalAssessment(
            domain_status="SUPPORTED" if signals else "INSUFFICIENT_EVIDENCE",
            assessment_status="SUPPORTED" if signals else "INSUFFICIENT",
            signals=tuple(signals),
            evidence_refs=refs,
        )

        claims: list[SemanticClaim] = []
        if self._input.cycle_turning_point_support is not None:
            item = self._input.cycle_turning_point_support
            claims.append(
                SemanticClaim(
                    claim_key=item.assertion_key,
                    claim_type="STATISTICAL_EVIDENCE",
                    statement=item.statement,
                    evidence_refs=item.evidence_refs,
                    assumption_refs=item.assumption_refs,
                )
            )
        for item in self._input.moat_evidence:
            claims.append(
                SemanticClaim(
                    claim_key=item.assertion_key,
                    claim_type="STATISTICAL_EVIDENCE",
                    statement=item.statement,
                    evidence_refs=item.evidence_refs,
                    assumption_refs=item.assumption_refs,
                )
            )
        if portfolio.primary is not None:
            claims.append(
                SemanticClaim(
                    claim_key=f"thesis:{portfolio.primary.thesis_key}",
                    claim_type="CONCLUSION",
                    statement=portfolio.primary.statement,
                    evidence_refs=portfolio.primary.evidence_refs,
                    assumption_refs=portfolio.primary.assumption_refs,
                )
            )
        semantic_claims = SemanticClaims(
            domain_status="SUPPORTED" if claims else "INSUFFICIENT_EVIDENCE",
            claims=tuple(claims),
            evidence_refs=refs,
        )
        status: ModuleStatus = (
            "PASS" if signals or claims or driver_keys else "INSUFFICIENT_EVIDENCE"
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            writes=(
                ArtifactWrite(
                    key=DRIVERS_GRAPH,
                    value=graph,
                    producer_id=self.spec.module_id,
                    evidence_refs=refs,
                ),
                ArtifactWrite(
                    key=THESIS_SEMANTIC_SIGNAL_ASSESSMENT,
                    value=assessment,
                    producer_id=self.spec.module_id,
                    evidence_refs=refs,
                ),
                ArtifactWrite(
                    key=SEMANTIC_CLAIMS,
                    value=semantic_claims,
                    producer_id=self.spec.module_id,
                    evidence_refs=refs,
                ),
            ),
        )
