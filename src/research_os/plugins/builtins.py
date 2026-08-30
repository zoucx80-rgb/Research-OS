from __future__ import annotations

from research_os.kpi.distributor import DistributorPack
from research_os.kpi.manufacturing import ManufacturingPack
from research_os.plugins.models import ApplicabilityResult, PluginManifest
from research_os.reporting.contributions import ReportContribution, ResearchQuestionSpec
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
        plugin_version="1.1.0",
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
        return [
            ReportContribution(
                contribution_id="manufacturing.operating_engine",
                section="Industry / Competitive Context",
                order=100,
                artifact_keys=["kpi.metrics", "drivers.graph"],
                title="Manufacturing operating engine",
                description="Connect production economics, capacity deployment and product mix to margin and cash generation.",
                research_questions=[
                    "What are the order, backlog and customer acceptance dynamics?",
                    "How are capacity, utilization, yield and product mix changing?",
                    "Which raw-material or qualification constraints can limit margin recovery?",
                ],
                question_specs=[
                    ResearchQuestionSpec(
                        question_id="manufacturing.orders_backlog",
                        text="What are the order, backlog and customer acceptance dynamics?",
                        required_capabilities=["manufacturing.orders"],
                        evidence_keys=["orders_backlog", "customer_acceptance"],
                    ),
                    ResearchQuestionSpec(
                        question_id="manufacturing.capacity_utilization",
                        text="How are capacity, utilization, yield and product mix changing?",
                        required_capabilities=["manufacturing.capacity"],
                        evidence_keys=["capacity", "capacity_utilization", "yield", "product_mix"],
                    ),
                    ResearchQuestionSpec(
                        question_id="manufacturing.raw_material_qualification",
                        text="Which raw-material or qualification constraints can limit margin recovery?",
                        required_capabilities=["manufacturing.constraints"],
                        evidence_keys=["raw_material_exposure", "qualification_cycle"],
                    ),
                ],
            ),
            ReportContribution(
                contribution_id="manufacturing.capital_cycle",
                section="Capital Efficiency & Funding Loop",
                order=110,
                artifact_keys=["kpi.metrics", "capital.efficiency", "capital.funding_loop"],
                title="Manufacturing capital cycle",
                description="Assess working-capital conversion, capex intensity and the return generated by the manufacturing asset base.",
                research_questions=[
                    "Is working capital converting to operating cash?",
                    "Is capex translating into productive capacity and capital returns?",
                    "Are receivables or inventory growing faster than operating activity?",
                ],
                question_specs=[
                    ResearchQuestionSpec(
                        question_id="manufacturing.cash_conversion",
                        text="Is working capital converting to operating cash?",
                        required_capabilities=["kpi.metrics"],
                        evidence_keys=["ocf", "ar_end", "inventory_end"],
                    ),
                    ResearchQuestionSpec(
                        question_id="manufacturing.capex_productivity",
                        text="Is capex translating into productive capacity and capital returns?",
                        required_capabilities=["kpi.metrics", "manufacturing.capacity"],
                        evidence_keys=["capex_cash", "capacity_utilization"],
                    ),
                    ResearchQuestionSpec(
                        question_id="manufacturing.working_capital_growth",
                        text="Are receivables or inventory growing faster than operating activity?",
                        required_capabilities=["kpi.metrics"],
                        evidence_keys=["revenue_growth", "ar_growth", "inventory_growth"],
                    ),
                ],
            ),
        ]


class DistributorIndustryPlugin:
    manifest = PluginManifest(
        plugin_id="industry:distributor",
        plugin_type="industry",
        plugin_version="1.2.0",
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
        return [
            ReportContribution(
                contribution_id="distributor.working_capital",
                section="Financial Quality",
                order=100,
                artifact_keys=["kpi.metrics", "capital.funding_loop", "drivers.graph"],
                title="Distributor working-capital engine",
                description="Connect receivables, inventory and payables to cash conversion and growth quality.",
                research_questions=[
                    "Are receivables and inventory growing faster than revenue?",
                    "How are DSO, DIO, DPO and the cash-conversion cycle changing?",
                    "Does gross profit adequately compensate for working-capital intensity?",
                ],
                question_specs=[
                    ResearchQuestionSpec(
                        question_id="distributor.working_capital_growth",
                        text="Are receivables and inventory growing faster than revenue?",
                        required_capabilities=["kpi.metrics"],
                        evidence_keys=["revenue_growth", "working_capital_growth"],
                    ),
                    ResearchQuestionSpec(
                        question_id="distributor.cash_conversion_cycle",
                        text="How are DSO, DIO, DPO and the cash-conversion cycle changing?",
                        required_capabilities=["kpi.metrics"],
                        evidence_keys=["avg_ar", "avg_inventory", "avg_ap", "revenue", "cogs"],
                    ),
                    ResearchQuestionSpec(
                        question_id="distributor.working_capital_return",
                        text="Does gross profit adequately compensate for working-capital intensity?",
                        required_capabilities=["kpi.metrics"],
                        evidence_keys=["gross_profit", "ar", "inventory", "ap"],
                    ),
                ],
            ),
            ReportContribution(
                contribution_id="distributor.financing_quality",
                section="Capital Efficiency & Funding Loop",
                order=110,
                artifact_keys=["kpi.metrics", "capital.funding_loop"],
                title="Distributor financing quality",
                description="Assess whether working-capital expansion is internally funded or dependent on debt, factoring and other external financing.",
                research_questions=[
                    "How much incremental working capital is debt funded?",
                    "How large are financing costs relative to gross profit?",
                    "How material are factoring or receivable-transfer exposures?",
                    "How sensitive is profit to inventory or credit impairment?",
                ],
                question_specs=[
                    ResearchQuestionSpec(
                        question_id="distributor.debt_funding",
                        text="How much incremental working capital is debt funded?",
                        required_capabilities=["kpi.metrics"],
                        evidence_keys=["delta_nwc", "delta_debt"],
                    ),
                    ResearchQuestionSpec(
                        question_id="distributor.financing_cost",
                        text="How large are financing costs relative to gross profit?",
                        required_capabilities=["kpi.metrics"],
                        evidence_keys=["financing_cost", "gross_profit"],
                    ),
                    ResearchQuestionSpec(
                        question_id="distributor.factoring_exposure",
                        text="How material are factoring or receivable-transfer exposures?",
                        required_capabilities=["kpi.metrics"],
                        evidence_keys=["factoring_balance", "derecognized_receivables", "receivable_transfer_balance"],
                    ),
                    ResearchQuestionSpec(
                        question_id="distributor.impairment_sensitivity",
                        text="How sensitive is profit to inventory or credit impairment?",
                        required_capabilities=["kpi.metrics"],
                        evidence_keys=["inventory_impairment", "credit_impairment", "gross_profit"],
                    ),
                ],
            ),
        ]


class BuiltinPluginProvider:
    def plugins(self):
        return [DistributorIndustryPlugin(), ManufacturingIndustryPlugin()]
