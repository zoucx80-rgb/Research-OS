from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from research_os.contracts.artifacts import ArtifactKey, ArtifactWrite
from research_os.contracts.evidence import EvidenceRef, EvidenceSet
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

EVIDENCE_PIT = ArtifactKey("evidence.pit", "2.0", EvidenceSet)


class FinancialFact(BaseModel):
    """One PIT-supported canonical financial fact for downstream projection."""

    model_config = ConfigDict(frozen=True)

    fact_key: str
    value: Any
    unit: str | None = None
    period: str | None = None
    period_end: date | None = None
    formula_version: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)


class FinancialFactSnapshot(BaseModel):
    """Decision-time financial facts without presentation-side recalculation."""

    model_config = ConfigDict(frozen=True)

    facts: tuple[FinancialFact, ...] = Field(default_factory=tuple)


FINANCIAL_FACT_SNAPSHOT = ArtifactKey(
    "financial.fact_snapshot", "2.0", FinancialFactSnapshot
)


def build_financial_fact_snapshot(context: ResearchContext) -> FinancialFactSnapshot:
    """Copy approved facts only when their as-of evidence supports the exact value."""

    facts: list[FinancialFact] = []

    for fact_key in SUPPORTED_FINANCIAL_FACT_KEYS:
        value = context.facts.get(fact_key)
        if value is None:
            continue

        supporting: list[tuple[EvidenceRef, Any]] = []
        for reference in context.facts.evidence_refs(fact_key):
            evidence = context.evidence.get(reference)
            if evidence is not None and (
                evidence.value == value or evidence.normalized_value == value
            ):
                supporting.append((reference, evidence))
        if not supporting:
            continue

        primary = supporting[0][1]
        facts.append(
            FinancialFact(
                fact_key=fact_key,
                value=value,
                unit=primary.unit,
                period=primary.period,
                period_end=primary.period_end,
                formula_version=primary.formula_version,
                evidence_refs=tuple(reference for reference, _ in supporting),
            )
        )

    return FinancialFactSnapshot(facts=tuple(facts))


class FinancialFactSnapshotModule:
    spec = ModuleSpec(
        module_id="core:financial-fact-snapshot",
        module_version="1.0.0",
        requires=frozenset((EVIDENCE_PIT,)),
        provides=frozenset((FINANCIAL_FACT_SNAPSHOT,)),
        required_for_completion=False,
    )

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        evidence = state.require(EVIDENCE_PIT)
        if not evidence.items:
            return ModuleResult(
                module_id=self.spec.module_id,
                status="INSUFFICIENT_EVIDENCE",
                writes=(
                    ArtifactWrite(
                        key=FINANCIAL_FACT_SNAPSHOT,
                        value=FinancialFactSnapshot(),
                        producer_id=self.spec.module_id,
                    ),
                ),
            )

        snapshot = build_financial_fact_snapshot(context)
        evidence_refs = tuple(
            reference
            for fact in snapshot.facts
            for reference in fact.evidence_refs
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS" if snapshot.facts else "INSUFFICIENT_EVIDENCE",
            writes=(
                ArtifactWrite(
                    key=FINANCIAL_FACT_SNAPSHOT,
                    value=snapshot,
                    producer_id=self.spec.module_id,
                    evidence_refs=evidence_refs,
                ),
            ),
        )
