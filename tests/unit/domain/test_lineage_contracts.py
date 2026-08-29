from datetime import datetime, timezone
import importlib
import importlib.util

import pytest

from research_os.domain.evidence import Evidence


def _load(name: str):
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, f"missing required module {name}"
    return importlib.import_module(name)


def test_evidence_can_preserve_raw_and_normalized_values_with_explicit_period_scope_version():
    e = Evidence(
        evidence_id="ev:gross_profit",
        company_id="001287.SZ",
        evidence_type="filing_fact",
        period_end="2026-06-30",
        period="2026H1",
        publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 8, 25, 1, tzinfo=timezone.utc),
        value=21.24,
        raw_value=21.24,
        normalized_value=2_124_000_000.0,
        unit="亿元",
        scope="consolidated",
        version="reported",
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
    )
    assert e.raw_value == 21.24
    assert e.normalized_value == 2_124_000_000.0
    assert e.period == "2026H1"
    assert e.version == "reported"


def test_calculation_lineage_records_formula_inputs_output_unit_and_version():
    m = _load("research_os.domain.lineage")
    item = m.CalculationLineage(
        formula="gross_profit = revenue - cogs",
        input_evidence_ids=["ev:revenue", "ev:cogs"],
        output=2_124_000_000.0,
        unit="元",
        calculation_version="finance-sanity@1.0.0",
    )
    assert item.input_evidence_ids == ["ev:revenue", "ev:cogs"]
    assert item.calculation_version == "finance-sanity@1.0.0"


def test_assumption_cannot_masquerade_as_fact():
    m = _load("research_os.domain.lineage")
    with pytest.raises(Exception):
        m.AssumptionLineage(
            label="FACT",
            value=0.5,
            unit="x",
            rationale="scenario multiple",
            source_evidence_ids=["ev:peer"],
        )
