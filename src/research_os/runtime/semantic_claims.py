from __future__ import annotations

from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.modules import ModuleResult, ModuleSpec
from research_os.semantics.claims import CycleAssessment, MoatAssessment


class SemanticClaimsModule:
    """Resolve cycle and moat wording from typed, generic evidence contracts."""

    spec = ModuleSpec(
        module_id="semantic:claims",
        module_version="1.0.0",
        requires=frozenset({"evidence.pit"}),
        provides=frozenset(
            {
                "semantic.cycle_assessment",
                "semantic.moat_assessment",
            }
        ),
        required_for_completion=False,
    )

    def __init__(self, *, inputs: ResearchInputs | None = None):
        self.inputs = inputs or ResearchInputs()

    def run(self, context, state) -> ModuleResult:
        cycle = None
        if self.inputs.cycle_turning_point_support is not None:
            cycle = CycleAssessment.assess(
                recovery_observed=bool(self.inputs.cycle_recovery_observed),
                turning_point_support=self.inputs.cycle_turning_point_support,
            )
        moat = (
            MoatAssessment.assess(self.inputs.moat_evidence)
            if self.inputs.moat_evidence
            else None
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS" if cycle is not None or moat is not None else "NOT_APPLICABLE",
            artifacts={
                "semantic.cycle_assessment": cycle,
                "semantic.moat_assessment": moat,
            },
            evidence_ids=list(
                dict.fromkeys(
                    evidence_id
                    for item in self.inputs.moat_evidence
                    for evidence_id in item.evidence_ids
                    if evidence_id
                )
            ),
        )
