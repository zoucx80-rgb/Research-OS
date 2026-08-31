from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from research_os.runtime.context import ResearchContext
from research_os.runtime.modules import ModuleResult, ModuleSpec
from research_os.runtime.state import ResearchStateView


SUPPORTED_FINANCIAL_FACT_KEYS: tuple[str, ...] = (
    "revenue",
    "revenue_growth",
    "net_profit_parent",
    "gross_profit",
    "gross_margin",
    "margin_change",
    "operating_cash_flow",
    "ocf",
    "capex_cash",
    "ar_begin",
    "ar_end",
    "ar_change",
    "ar_growth",
    "inventory_begin",
    "inventory_end",
    "inventory_change",
    "inventory_growth",
    "debt_begin",
    "debt_end",
    "debt_change",
    "ppe_begin",
    "ppe_end",
)


class FinancialFact(BaseModel):
    """One PIT-supported canonical financial fact for downstream projection."""

    model_config = ConfigDict(frozen=True)

    fact_key: str
    value: Any
    unit: str | None = None
    period: str | None = None
    period_end: date | None = None
    formula_version: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class FinancialFactSnapshot(BaseModel):
    """Decision-time financial facts without presentation-side recalculation."""

    model_config = ConfigDict(frozen=True)

    facts: list[FinancialFact] = Field(default_factory=list)


def build_financial_fact_snapshot(context: ResearchContext) -> FinancialFactSnapshot:
    """Copy approved facts only when their as-of evidence supports the exact value."""

    pit_ids = {
        item.evidence_id
        for item in context.evidence.as_of(context.decision_ts)
    }
    facts: list[FinancialFact] = []

    for fact_key in SUPPORTED_FINANCIAL_FACT_KEYS:
        value = context.facts.get(fact_key)
        if value is None:
            continue

        supporting = []
        for evidence_id in context.facts.evidence_ids(fact_key):
            if evidence_id not in pit_ids:
                continue
            evidence = context.evidence.get(evidence_id)
            if evidence is not None and evidence.value == value:
                supporting.append(evidence)
        if not supporting:
            continue

        primary = supporting[0]
        facts.append(
            FinancialFact(
                fact_key=fact_key,
                value=value,
                unit=primary.unit,
                period=primary.period,
                period_end=primary.period_end,
                formula_version=primary.formula_version,
                evidence_ids=[item.evidence_id for item in supporting],
            )
        )

    return FinancialFactSnapshot(facts=facts)


class FinancialFactSnapshotModule:
    spec = ModuleSpec(
        module_id="core:financial-fact-snapshot",
        module_version="1.0.0",
        requires={"evidence.pit"},
        provides={"financial.fact_snapshot"},
        required_for_completion=False,
    )

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        if not list(state.get("evidence.pit", []) or []):
            return ModuleResult(
                module_id=self.spec.module_id,
                status="INSUFFICIENT_EVIDENCE",
                artifacts={"financial.fact_snapshot": FinancialFactSnapshot()},
            )

        snapshot = build_financial_fact_snapshot(context)
        evidence_ids = list(
            dict.fromkeys(
                evidence_id
                for item in snapshot.facts
                for evidence_id in item.evidence_ids
            )
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS" if snapshot.facts else "INSUFFICIENT_EVIDENCE",
            artifacts={"financial.fact_snapshot": snapshot},
            evidence_ids=evidence_ids,
        )
