from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_os.contracts.artifacts import ArtifactKey, ArtifactWrite
from research_os.contracts.evidence import EvidenceRef, EvidenceSet
from research_os.contracts.values import (
    AccountingScope,
    FinancialValue,
    Money,
    Quantity,
    Ratio,
)
from research_os.period.models import ReportingPeriod
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

    model_config = ConfigDict(frozen=True, extra="forbid")

    fact_key: str
    value: FinancialValue
    reporting_period: ReportingPeriod
    accounting_scope: AccountingScope
    formula_version: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)

    @field_validator("fact_key")
    @classmethod
    def _fact_key_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("fact_key must be non-empty")
        return normalized


class FinancialFactSnapshot(BaseModel):
    """Decision-time financial facts without presentation-side recalculation."""

    model_config = ConfigDict(frozen=True)

    facts: tuple[FinancialFact, ...] = Field(default_factory=tuple)


FINANCIAL_FACT_SNAPSHOT = ArtifactKey("financial.fact_snapshot", "2.0", FinancialFactSnapshot)


_RATIO_FACT_KEYS = frozenset(
    {
        "revenue_growth",
        "gross_margin",
        "margin_change",
        "ar_growth",
        "inventory_growth",
    }
)
_CURRENCY_UNIT = re.compile(
    r"^(?P<currency>[A-Za-z]{3})(?:_(?P<scale>\d+(?:\.\d+)?)(?P<suffix>[KMBT])?)?$"
)
_SCALE_SUFFIXES = {
    None: Decimal(1),
    "K": Decimal(1_000),
    "M": Decimal(1_000_000),
    "B": Decimal(1_000_000_000),
    "T": Decimal(1_000_000_000_000),
}


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        resolved = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return resolved if resolved.is_finite() else None


def _typed_financial_value(
    fact_key: str,
    value: object,
    unit: str | None,
) -> FinancialValue | None:
    if isinstance(value, (Money, Ratio, Quantity)):
        return value
    numeric = _decimal(value)
    if numeric is None:
        return None

    normalized_unit = unit.strip() if unit is not None else None
    if fact_key in _RATIO_FACT_KEYS:
        representation: Literal["decimal", "percent", "basis_points"] = (
            "percent"
            if normalized_unit in {"%", "percent", "percentage_point"}
            else "basis_points"
            if normalized_unit in {"bp", "bps", "basis_points"}
            else "decimal"
        )
        return Ratio(value=numeric, representation=representation)

    if normalized_unit in {"%", "percent", "percentage_point"}:
        return Ratio(value=numeric, representation="percent")
    if normalized_unit in {"bp", "bps", "basis_points"}:
        return Ratio(value=numeric, representation="basis_points")
    if normalized_unit in {"元", "人民币元"}:
        return Money(amount=numeric, currency="CNY")
    if normalized_unit in {"亿元", "人民币亿元"}:
        return Money(amount=numeric, currency="CNY", scale=100_000_000)
    if normalized_unit is not None:
        match = _CURRENCY_UNIT.fullmatch(normalized_unit)
        if match is not None:
            number = Decimal(match.group("scale") or 1)
            scale = number * _SCALE_SUFFIXES[match.group("suffix")]
            if scale == scale.to_integral_value() and scale > 0:
                return Money(
                    amount=numeric,
                    currency=match.group("currency"),
                    scale=int(scale),
                )
        return Quantity(value=numeric, unit=normalized_unit)
    return None


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
        typed_value = _typed_financial_value(fact_key, value, primary.unit)
        if typed_value is None:
            continue
        facts.append(
            FinancialFact(
                fact_key=fact_key,
                value=typed_value,
                reporting_period=context.facts.reporting_period,
                accounting_scope=context.facts.accounting_scope,
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
            reference for fact in snapshot.facts for reference in fact.evidence_refs
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
