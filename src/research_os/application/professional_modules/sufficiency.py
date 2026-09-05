"""Engine module for domain-level research sufficiency."""

from __future__ import annotations

from research_os.contracts.artifacts import ArtifactWrite
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import (
    FINANCIAL_TEMPORAL_ANALYSIS,
    METHODOLOGY_DISCLOSURE,
    RESEARCH_SUFFICIENCY,
)
from research_os.runtime.modules import ModuleResult, ModuleSpec
from research_os.runtime.state import ResearchStateView
from research_os.sufficiency.service import ResearchSufficiencyEvaluator


class ResearchSufficiencyModule:
    spec = ModuleSpec(
        module_id="core:research-sufficiency",
        module_version="2.0.0",
        requires=frozenset((FINANCIAL_TEMPORAL_ANALYSIS, METHODOLOGY_DISCLOSURE)),
        provides=frozenset((RESEARCH_SUFFICIENCY,)),
        required_for_completion=False,
    )

    def __init__(self) -> None:
        self._evaluator = ResearchSufficiencyEvaluator()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        del context
        state.require(METHODOLOGY_DISCLOSURE)
        assessment = self._evaluator.evaluate(state)
        return ModuleResult(
            module_id=self.spec.module_id,
            status=(
                "PASS"
                if assessment.overall_status in {"SUFFICIENT", "LIMITED"}
                else "INSUFFICIENT_EVIDENCE"
            ),
            writes=(
                ArtifactWrite(
                    key=RESEARCH_SUFFICIENCY,
                    value=assessment,
                    producer_id=self.spec.module_id,
                    evidence_refs=assessment.evidence_refs,
                ),
            ),
        )
