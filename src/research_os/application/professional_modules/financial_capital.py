"""Focused professional research modules: financial capital."""

from __future__ import annotations

from decimal import Decimal

from research_os.application.command import ResearchRunCommand
from research_os.capital.engine import CapitalEfficiencyEngine
from research_os.contracts.artifact_values import CapitalEfficiency
from research_os.contracts.artifact_values import CashFlowQualityBridge
from research_os.contracts.artifact_values import FinancialTimeSeriesSet
from research_os.contracts.artifact_values import FinancialValidation
from research_os.contracts.artifact_values import FundingLoop
from research_os.contracts.artifact_values import OperatingEvidenceSet
from research_os.contracts.artifacts import ArtifactWrite
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import CAPITAL_EFFICIENCY
from research_os.runtime.core_artifacts import CAPITAL_FUNDING_LOOP
from research_os.runtime.core_artifacts import CASH_FLOW_QUALITY_BRIDGE
from research_os.runtime.core_artifacts import FINANCIAL_TIME_SERIES
from research_os.runtime.core_artifacts import RESEARCH_OPERATING_EVIDENCE
from research_os.runtime.core_artifacts import VALIDATION_FINANCIAL
from research_os.runtime.modules import ModuleResult
from research_os.runtime.modules import ModuleSpec
from research_os.runtime.modules import ModuleStatus
from research_os.runtime.state import ResearchStateView
from research_os.application.professional_modules._common import _fact_refs, _lineage_refs


class FinancialResearchModule:
    spec = ModuleSpec(
        module_id="core:professional-financial",
        module_version="2.0.1",
        requires=frozenset(),
        provides=frozenset(
            (
                FINANCIAL_TIME_SERIES,
                RESEARCH_OPERATING_EVIDENCE,
                CASH_FLOW_QUALITY_BRIDGE,
                VALIDATION_FINANCIAL,
            )
        ),
        required_for_completion=False,
    )

    def __init__(self, command: ResearchRunCommand) -> None:
        self._input = command.financial

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        time_refs = _lineage_refs(self._input.time_series)
        operating_refs = _lineage_refs(self._input.operating_observations)
        cash_input = self._input.cash_flow_quality
        cash_refs = _lineage_refs(cash_input) if cash_input is not None else ()
        all_refs = _lineage_refs(time_refs, operating_refs, cash_refs)

        time_series = FinancialTimeSeriesSet(
            domain_status="SUPPORTED" if self._input.time_series else "INSUFFICIENT_EVIDENCE",
            series=self._input.time_series,
            evidence_refs=time_refs,
        )
        operating = OperatingEvidenceSet(
            domain_status=(
                "SUPPORTED" if self._input.operating_observations else "INSUFFICIENT_EVIDENCE"
            ),
            observations=self._input.operating_observations,
            evidence_refs=operating_refs,
        )
        if cash_input is None:
            bridge = CashFlowQualityBridge()
        else:
            simplified_fcf = (
                None
                if cash_input.operating_cash_flow is None or cash_input.capex_cash is None
                else Decimal(str(cash_input.operating_cash_flow))
                - Decimal(str(cash_input.capex_cash))
            )
            bridge = CashFlowQualityBridge(
                domain_status=(
                    "SUPPORTED"
                    if any(
                        value is not None
                        for value in (
                            cash_input.net_profit,
                            cash_input.operating_cash_flow,
                            cash_input.working_capital_contribution,
                            cash_input.other_adjustments,
                            cash_input.capex_cash,
                        )
                    )
                    else "INSUFFICIENT_EVIDENCE"
                ),
                net_profit=cash_input.net_profit,
                operating_cash_flow=cash_input.operating_cash_flow,
                working_capital_contribution=cash_input.working_capital_contribution,
                other_adjustments=cash_input.other_adjustments,
                capex_cash=cash_input.capex_cash,
                simplified_fcf=simplified_fcf,
                unit=cash_input.unit,
                evidence_refs=cash_refs,
                assumption_refs=cash_input.assumption_refs,
            )
        validation = FinancialValidation(
            domain_status="SUPPORTED" if all_refs else "INSUFFICIENT_EVIDENCE",
            validation_status="PASS" if all_refs else "INSUFFICIENT_EVIDENCE",
            evidence_refs=all_refs,
        )
        status: ModuleStatus = "PASS" if all_refs else "INSUFFICIENT_EVIDENCE"
        writes = (
            ArtifactWrite(
                key=FINANCIAL_TIME_SERIES,
                value=time_series,
                producer_id=self.spec.module_id,
                evidence_refs=time_refs,
            ),
            ArtifactWrite(
                key=RESEARCH_OPERATING_EVIDENCE,
                value=operating,
                producer_id=self.spec.module_id,
                evidence_refs=operating_refs,
            ),
            ArtifactWrite(
                key=CASH_FLOW_QUALITY_BRIDGE,
                value=bridge,
                producer_id=self.spec.module_id,
                evidence_refs=cash_refs,
            ),
            ArtifactWrite(
                key=VALIDATION_FINANCIAL,
                value=validation,
                producer_id=self.spec.module_id,
                evidence_refs=all_refs,
            ),
        )
        return ModuleResult(module_id=self.spec.module_id, status=status, writes=writes)


class CapitalResearchModule:
    spec = ModuleSpec(
        module_id="core:professional-capital",
        module_version="2.0.1",
        requires=frozenset(),
        provides=frozenset((CAPITAL_EFFICIENCY, CAPITAL_FUNDING_LOOP)),
        required_for_completion=False,
    )

    _FACT_IDS = (
        "invested_capital_begin",
        "invested_capital_end",
        "invested_capital_prev",
        "nopat",
        "nopat_prev",
        "delta_nwc",
        "delta_revenue",
        "delta_debt",
        "delta_equity",
        "external_equity_financing",
        "operating_cash_flow",
        "factoring_balance",
        "derecognized_receivables",
        "receivable_transfer_balance",
        "other_working_capital_financing",
        "ar",
        "equity_dilution",
        "delta_nwc_comparison_basis",
        "delta_revenue_comparison_basis",
        "delta_debt_comparison_basis",
        "external_equity_financing_comparison_basis",
    )

    def __init__(self) -> None:
        self._engine = CapitalEfficiencyEngine()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        facts = context.facts.as_mapping()
        efficiency_result = self._engine.calculate(facts)
        funding_result = self._engine.funding_loop(facts)
        refs = _fact_refs(
            context, (key for key in self._FACT_IDS if context.facts.get(key) is not None)
        )

        efficiency_supported = any(
            value is not None
            for value in (
                efficiency_result.roic,
                efficiency_result.incremental_roic,
                efficiency_result.iwcr,
            )
        )
        efficiency = CapitalEfficiency(
            domain_status="SUPPORTED" if efficiency_supported else "INSUFFICIENT_EVIDENCE",
            roic=efficiency_result.roic,
            incremental_roic=efficiency_result.incremental_roic,
            iwcr=efficiency_result.iwcr,
            evidence_refs=refs,
        )
        funding_supported = funding_result.funding_state != "unknown" or bool(
            funding_result.reason_codes
        )
        funding = FundingLoop(
            domain_status="SUPPORTED" if funding_supported else "INSUFFICIENT_EVIDENCE",
            funding_state=funding_result.funding_state,
            reason_codes=tuple(
                dict.fromkeys(
                    (*funding_result.reason_codes, *funding_result.comparison_basis_errors)
                )
            ),
            evidence_refs=refs,
        )
        status: ModuleStatus = (
            "PASS" if efficiency_supported or funding_supported else "INSUFFICIENT_EVIDENCE"
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            writes=(
                ArtifactWrite(
                    key=CAPITAL_EFFICIENCY,
                    value=efficiency,
                    producer_id=self.spec.module_id,
                    evidence_refs=refs,
                ),
                ArtifactWrite(
                    key=CAPITAL_FUNDING_LOOP,
                    value=funding,
                    producer_id=self.spec.module_id,
                    evidence_refs=refs,
                ),
            ),
        )
