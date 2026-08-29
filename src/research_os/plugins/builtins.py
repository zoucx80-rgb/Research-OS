from __future__ import annotations

from research_os.kpi.distributor import DistributorPack
from research_os.kpi.manufacturing import ManufacturingPack
from research_os.plugins.models import ApplicabilityResult, PluginManifest
from research_os.runtime.context import ResearchContext
from research_os.runtime.modules import ModuleResult, ModuleSpec
from research_os.runtime.state import ResearchStateView


class _KpiPackAdapterModule:
    def __init__(self, plugin_id: str, pack):
        self._pack = pack
        self.spec = ModuleSpec(
            module_id=f"{plugin_id}:kpi",
            module_version=pack.pack_version,
            requires={"business_model.profile"},
            provides={"kpi.metrics"},
        )

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        facts = context.facts.as_mapping()
        metrics = self._pack.calculate(facts)
        missing_required = sorted(
            fact for fact in self._pack.required_facts if context.facts.get(fact) is None
        )
        evidence_ids = sorted({
            evidence_id
            for fact in self._pack.required_facts | self._pack.optional_facts
            for evidence_id in context.facts.evidence_ids(fact)
        })
        return ModuleResult(
            module_id=self.spec.module_id,
            status="INSUFFICIENT_EVIDENCE" if missing_required else "PASS",
            artifacts={"kpi.metrics": metrics},
            evidence_ids=evidence_ids,
            diagnostics=(
                ["missing required facts: " + ", ".join(missing_required)]
                if missing_required
                else []
            ),
        )


class ManufacturingIndustryPlugin:
    manifest = PluginManifest(
        plugin_id="industry:manufacturing",
        plugin_type="industry",
        plugin_version="1.0.0",
        api_version="1.0",
        min_research_os_version="1.3.0",
        provides={"kpi.metrics"},
        requires={"business_model.profile"},
        supported_business_models={"manufacturing", "manufacturer"},
        priority=100,
        maturity="stable",
    )

    def __init__(self):
        self._pack = ManufacturingPack()

    def applicability(self, context: ResearchContext) -> ApplicabilityResult:
        return ApplicabilityResult(
            applicable=True,
            score=1.0,
            rationale=["built-in manufacturing strategy"],
        )

    def modules(self):
        return [_KpiPackAdapterModule(self.manifest.plugin_id, self._pack)]

    def report_contributions(self):
        return []


class DistributorIndustryPlugin:
    manifest = PluginManifest(
        plugin_id="industry:distributor",
        plugin_type="industry",
        plugin_version="1.0.0",
        api_version="1.0",
        min_research_os_version="1.3.0",
        provides={"kpi.metrics"},
        requires={"business_model.profile"},
        supported_business_models={"distributor"},
        priority=100,
        maturity="stable",
    )

    def __init__(self):
        self._pack = DistributorPack()

    def applicability(self, context: ResearchContext) -> ApplicabilityResult:
        return ApplicabilityResult(
            applicable=True,
            score=1.0,
            rationale=["built-in distributor strategy"],
        )

    def modules(self):
        return [_KpiPackAdapterModule(self.manifest.plugin_id, self._pack)]

    def report_contributions(self):
        return []


class BuiltinPluginProvider:
    def plugins(self):
        return [DistributorIndustryPlugin(), ManufacturingIndustryPlugin()]
