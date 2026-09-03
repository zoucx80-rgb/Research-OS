from __future__ import annotations

from typing import TYPE_CHECKING, Any

from research_os.contracts.metrics import MetricResult as ContractMetricResult
from research_os.contracts.policies import PolicySnapshot
from research_os.kpi.distributor import DistributorPack
from research_os.kpi.manufacturing import ManufacturingPack
from research_os.metrics import MetricCalculationEngine
from research_os.plugins.models import ApplicabilityResult, PluginManifest
from research_os.plugins.protocols import PluginServices, ResearchPlugin
from research_os.reporting.contributions import ReportContribution, ResearchQuestionSpec
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import FactView, ResearchContext

if TYPE_CHECKING:
    from research_os.plugins.protocols import MetricDefinitionRegistry


class _BuiltinKpiProvider:
    def __init__(self, *, provider_id: str, pack: Any):
        self.provider_id = provider_id
        self.provider_version = pack.pack_version.rsplit("@", 1)[-1]
        self.__metric_ids = frozenset(pack.metric_ids)
        self.__calculator = MetricCalculationEngine()

    def metric_ids(self) -> frozenset[str]:
        return self.__metric_ids

    def calculate(
        self,
        facts: FactView,
        definitions: MetricDefinitionRegistry,
        policy: PolicySnapshot,
    ) -> tuple[ContractMetricResult, ...]:
        results: list[ContractMetricResult] = []
        for metric_id in sorted(self.__metric_ids):
            definition = definitions.get(metric_id)
            if definition is None:
                raise ValueError(f"undefined metric: {metric_id}")
            results.append(self.__calculator.calculate(facts, definition, policy))
        return tuple(results)


class ManufacturingIndustryPlugin:
    manifest = PluginManifest(
        plugin_id="industry:manufacturing",
        plugin_type="industry",
        plugin_version="2.0.0",
        plugin_api_version="2.0",
        core_api_specifier="~=2.0",
        research_os_specifier=">=1.6,<2",
        supported_business_models=frozenset({"manufacturing", "manufacturer"}),
        service_capabilities=frozenset({"kpi.metrics", "report.contributions"}),
        priority=100,
        maturity="stable",
    )

    def __init__(self) -> None:
        self._services = PluginServices(
            kpi_provider=_BuiltinKpiProvider(
                provider_id="industry:manufacturing:kpi", pack=ManufacturingPack()
            ),
            report_contributions=tuple(self._report_contributions()),
        )

    def applicability(
        self,
        context: ResearchContext,
        business_model: BusinessModelProfile,
    ) -> ApplicabilityResult:
        applicable = business_model.primary_model in self.manifest.supported_business_models
        return ApplicabilityResult(
            applicable=applicable,
            rule_score=1.0 if applicable else 0.0,
            rationale=("built-in manufacturing strategy",),
            evidence_refs=business_model.evidence_refs,
        )

    def services(self) -> PluginServices:
        return self._services

    def _report_contributions(self) -> list[ReportContribution]:
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
        plugin_version="2.0.0",
        plugin_api_version="2.0",
        core_api_specifier="~=2.0",
        research_os_specifier=">=1.6,<2",
        supported_business_models=frozenset({"distributor"}),
        service_capabilities=frozenset({"kpi.metrics", "report.contributions"}),
        priority=100,
        maturity="stable",
    )

    def __init__(self) -> None:
        self._services = PluginServices(
            kpi_provider=_BuiltinKpiProvider(
                provider_id="industry:distributor:kpi", pack=DistributorPack()
            ),
            report_contributions=tuple(self._report_contributions()),
        )

    def applicability(
        self,
        context: ResearchContext,
        business_model: BusinessModelProfile,
    ) -> ApplicabilityResult:
        applicable = business_model.primary_model in self.manifest.supported_business_models
        return ApplicabilityResult(
            applicable=applicable,
            rule_score=1.0 if applicable else 0.0,
            rationale=("built-in distributor strategy",),
            evidence_refs=business_model.evidence_refs,
        )

    def services(self) -> PluginServices:
        return self._services

    def _report_contributions(self) -> list[ReportContribution]:
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
    def plugins(self) -> tuple[ResearchPlugin, ...]:
        return (DistributorIndustryPlugin(), ManufacturingIndustryPlugin())
