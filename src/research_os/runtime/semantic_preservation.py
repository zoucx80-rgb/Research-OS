from __future__ import annotations

from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.modules import ModuleResult, ModuleSpec
from research_os.semantics.preservation import SemanticPreservationValidator


class SemanticPreservationModule:
    """Validate that result-bearing research artifacts retain material qualifiers."""

    spec = ModuleSpec(
        module_id="semantic:preservation",
        module_version="1.0.0",
        requires=frozenset({"evidence.pit"}),
        provides=frozenset(
            {
                "semantic.preservation",
                "validation.semantic_preservation",
            }
        ),
        required_for_completion=False,
    )

    def __init__(self, *, inputs: ResearchInputs | None = None):
        self.inputs = inputs or ResearchInputs()

    def run(self, context, state) -> ModuleResult:
        validation = SemanticPreservationValidator.validate(
            sensitivities=self.inputs.sensitivities,
            monitoring_rules=self.inputs.monitoring_rules,
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=validation.status,
            artifacts={
                "semantic.preservation": validation,
                "validation.semantic_preservation": validation,
            },
            diagnostics=[item.code for item in validation.violations],
        )
