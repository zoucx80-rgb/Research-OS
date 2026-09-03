from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from research_os.contracts.values import (
    AccountingScope,
    Money,
    Quantity,
    Ratio,
)
from research_os.contracts.evidence import EvidenceRef
from research_os.domain.evidence import Evidence
from research_os.domain.lineage import (
    AssumptionLineage,
    CalculationLineage,
    InferenceLineage,
)
from research_os.period.models import ReportingPeriod
from research_os.runtime.financial_snapshot import FinancialFact


def test_money_preserves_currency_scale_and_normalizes_currency_code() -> None:
    value = Money(amount="12.345", currency="cny", scale=100_000_000)

    assert value.amount == Decimal("12.345")
    assert value.currency == "CNY"
    assert value.scale == 100_000_000
    assert value.base_amount == Decimal("1234500000.000")


def test_money_addition_normalizes_scale_but_rejects_currency_mismatch() -> None:
    left = Money(amount="1.25", currency="CNY", scale=100)
    right = Money(amount="25", currency="CNY", scale=1)

    assert left + right == Money(amount="1.50", currency="CNY", scale=100)
    with pytest.raises(ValueError, match="currency"):
        _ = left + Money(amount="1", currency="USD", scale=100)
    with pytest.raises(ValueError, match="currency"):
        _ = left < Money(amount="2", currency="USD", scale=100)


def test_ratio_representation_is_explicit_and_comparisons_use_decimal_value() -> None:
    decimal = Ratio(value="0.125", representation="decimal")
    percent = Ratio(value="12.5", representation="percent")
    basis_points = Ratio(value="1250", representation="basis_points")

    assert decimal.decimal_value == Decimal("0.125")
    assert decimal == percent == basis_points
    assert Ratio(value="12.6", representation="percent") > decimal


def test_quantity_operations_require_the_same_unit() -> None:
    shares = Quantity(value="10", unit="million_shares")

    assert shares + Quantity(value="2", unit="million_shares") == Quantity(
        value="12", unit="million_shares"
    )
    with pytest.raises(ValueError, match="unit"):
        _ = shares + Quantity(value="2", unit="tonnes")
    with pytest.raises(ValueError, match="unit"):
        _ = shares >= Quantity(value="2", unit="tonnes")


def test_financial_values_reject_non_finite_values_and_invalid_scale() -> None:
    with pytest.raises(ValidationError, match="finite"):
        Money(amount="NaN", currency="CNY")
    with pytest.raises(ValidationError, match="scale"):
        Money(amount="1", currency="CNY", scale=0)
    with pytest.raises(ValidationError, match="finite"):
        Ratio(value="Infinity", representation="decimal")


def test_accounting_scope_distinguishes_every_material_dimension() -> None:
    base = AccountingScope(
        accounting_standard="IFRS",
        consolidation="consolidated",
        segment="industrial",
        geography="global",
        continuing_operations=True,
    )

    variants = (
        base.model_copy(update={"accounting_standard": "PRC_GAAP"}),
        base.model_copy(update={"consolidation": "standalone"}),
        base.model_copy(update={"segment": "consumer"}),
        base.model_copy(update={"geography": "China"}),
        base.model_copy(update={"continuing_operations": False}),
    )
    assert all(not base.is_comparable_with(item) for item in variants)
    for item in variants:
        with pytest.raises(ValueError, match="accounting scope"):
            base.require_comparable(item)


def test_evidence_requires_timezone_aware_times_and_normalizes_them_to_utc() -> None:
    common = {
        "evidence_id": "ev:revenue",
        "company_id": "company:1",
        "evidence_type": "filing_fact",
        "confidence_grade": "A",
        "verification_status": "PRIMARY_VERIFIED",
    }
    with pytest.raises(ValidationError, match="timezone-aware"):
        Evidence(
            **common,
            publish_ts=datetime(2026, 8, 1, 9),
            ingested_at=datetime(2026, 8, 1, 10, tzinfo=timezone.utc),
        )

    value = Evidence(
        **common,
        publish_ts=datetime(2026, 8, 1, 9, tzinfo=timezone(timedelta(hours=8))),
        ingested_at=datetime(2026, 8, 1, 10, tzinfo=timezone(timedelta(hours=8))),
    )

    assert value.publish_ts == datetime(2026, 8, 1, 1, tzinfo=timezone.utc)
    assert value.ingested_at == datetime(2026, 8, 1, 2, tzinfo=timezone.utc)


def test_financial_fact_requires_a_typed_value_period_scope_and_revision_lineage() -> None:
    reference = EvidenceRef(
        evidence_id="ev:revenue",
        revision=1,
        content_fingerprint="a" * 64,
    )
    fact = FinancialFact(
        fact_key="revenue",
        value=Money(amount="12.5", currency="CNY", scale=100_000_000),
        reporting_period=ReportingPeriod(period_type="H1"),
        accounting_scope=AccountingScope(consolidation="consolidated"),
        formula_version="reported@1",
        evidence_refs=(reference,),
    )

    assert fact.value.base_amount == Decimal("1250000000.0")
    with pytest.raises(ValidationError):
        FinancialFact(
            fact_key="revenue",
            value=12.5,
            reporting_period=ReportingPeriod(period_type="H1"),
            accounting_scope=AccountingScope(),
            evidence_refs=(reference,),
        )


def test_lineage_keeps_calculations_assumptions_and_inferences_distinct() -> None:
    reference = EvidenceRef(
        evidence_id="ev:revenue",
        revision=1,
        content_fingerprint="b" * 64,
    )
    calculation = CalculationLineage(
        formula="growth = current / prior - 1",
        input_evidence_refs=(reference,),
        output=Ratio(value="0.1", representation="decimal"),
        calculation_version="growth@1",
    )
    assumption = AssumptionLineage(
        value=Ratio(value="8", representation="percent"),
        rationale="base-case growth assumption",
        source_evidence_refs=(reference,),
    )
    inference = InferenceLineage(
        statement="growth is moderating",
        evidence_refs=(reference,),
        confidence_grade="B",
    )

    assert calculation.lineage_type == "CALCULATION"
    assert assumption.lineage_type == "ANALYST_ASSUMPTION"
    assert inference.lineage_type == "INFERENCE"
    with pytest.raises(ValidationError):
        CalculationLineage(
            formula="growth = current / prior - 1",
            input_evidence_ids=["ev:revenue"],
            output=0.1,
            calculation_version="growth@1",
        )
