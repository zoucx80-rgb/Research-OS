from __future__ import annotations

from datetime import timezone
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import subprocess
from types import ModuleType

import pytest

from research_os.application import ResearchApplication, ResearchRunCommand
from research_os.period.models import ReportingPeriod
from research_os.runtime.core_artifacts import (
    FINANCIAL_TEMPORAL_ANALYSIS,
    RESEARCH_SUFFICIENCY,
)
from research_os.temporal.models import FinancialPeriodObservation, PeriodKind


SCRIPT = Path("scripts/render_field_acceptance_v1_6_01.py")
CASES = Path("tests/fixtures/field_acceptance/v1_6_01/cases.json")

_METRICS: dict[str, tuple[tuple[str, str, PeriodKind, str], ...]] = {
    "300034.SZ": (
        ("revenue", "revenue", "FLOW", "CNY"),
        ("gross_margin", "gross_margin", "FLOW_RATIO", "ratio"),
        ("operating_cash_flow", "operating_cash_flow", "FLOW", "CNY"),
    ),
    "001287.SZ": (
        ("revenue", "revenue", "FLOW", "CNY"),
        ("ar", "ar", "STOCK", "CNY"),
        ("inventory", "inventory", "STOCK", "CNY"),
        ("delta_nwc", "delta_nwc", "FLOW", "CNY"),
        ("operating_cash_flow", "operating_cash_flow", "FLOW", "CNY"),
        ("short_debt", "short_debt", "STOCK", "CNY"),
    ),
    "301073.SZ": (
        ("revenue", "revenue", "FLOW", "CNY"),
        ("operating_cash_flow", "operating_cash_flow", "FLOW", "CNY"),
        ("lease_liabilities_to_assets", "lease_liabilities_to_assets", "STOCK_RATIO", "ratio"),
    ),
}


def _runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("field_acceptance_v1_6_01", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _case(runner: ModuleType, company_id: str) -> dict[str, object]:
    manifest = json.loads(CASES.read_text(encoding="utf-8"))
    case_spec = next(item for item in manifest["cases"] if item["case_id"] == company_id)
    return runner._merge_case(Path.cwd(), case_spec)


def _period_observations(
    command: ResearchRunCommand,
    company_id: str,
) -> tuple[FinancialPeriodObservation, ...]:
    observations = []
    source_period = command.context.facts.reporting_period
    for metric_id, fact_id, period_kind, unit in _METRICS[company_id]:
        value = command.context.facts.get(fact_id)
        references = command.context.facts.evidence_refs(fact_id)
        assert value is not None, fact_id
        assert references, fact_id
        evidence = tuple(command.context.evidence.get(reference) for reference in references)
        assert all(item is not None for item in evidence)
        available_ts = max(item.publish_ts for item in evidence if item is not None).astimezone(
            timezone.utc
        )
        reporting_period = source_period
        if period_kind in {"STOCK", "STOCK_RATIO"}:
            reporting_period = ReportingPeriod(
                period_type=source_period.period_type,
                period_end=source_period.period_end,
                is_cumulative=False,
            )
        observations.append(
            FinancialPeriodObservation(
                metric_id=metric_id,
                reporting_period=reporting_period,
                period_kind=period_kind,
                value=Decimal(str(value)),
                unit=unit,
                accounting_scope=command.context.facts.accounting_scope,
                value_kind=("derived" if fact_id.endswith("_to_assets") else "reported"),
                comparison_basis="YOY_PERIOD",
                available_ts=available_ts,
                evidence_refs=references,
            )
        )
    return tuple(observations)


def _run(company_id: str):
    runner = _runner()
    commit_sha = subprocess.check_output(("git", "rev-parse", "HEAD"), text=True).strip()
    command = runner._command(_case(runner, company_id), commit_sha=commit_sha)
    command = command.model_copy(
        update={
            "financial": command.financial.model_copy(
                update={
                    "period_observations": _period_observations(command, company_id),
                }
            )
        }
    )
    result = ResearchApplication.build(repository_attestor=runner._Attestor(commit_sha)).run(
        command
    )
    return result


@pytest.mark.parametrize("company_id", ("300034.SZ", "001287.SZ", "301073.SZ"))
def test_single_period_case_is_not_temporally_sufficient(company_id: str) -> None:
    result = _run(company_id)

    temporal = result.artifacts.require(FINANCIAL_TEMPORAL_ANALYSIS)
    sufficiency = result.artifacts.require(RESEARCH_SUFFICIENCY)
    expected_metrics = {item[0] for item in _METRICS[company_id]}

    assert temporal.temporal_coverage == "INSUFFICIENT_EVIDENCE"
    assert {item.metric_id for item in temporal.assessments} == expected_metrics
    assert all(item.point_count == 1 for item in temporal.assessments)
    assert all(item.comparison_status == "INSUFFICIENT_EVIDENCE" for item in temporal.assessments)
    assert all(item.comparison_basis == "YOY_PERIOD" for item in temporal.assessments)
    assert all(item.evidence_refs for item in temporal.assessments)

    domain = sufficiency.require_domain("financial_temporal")
    assert domain.temporal_coverage == "MISSING"
    assert domain.unknown_items == tuple(
        f"comparable_trend:{metric_id}" for metric_id in sorted(expected_metrics)
    )
    assert set(domain.why_unknown) == {
        f"{metric_id}:INSUFFICIENT_COMPARABLE_POINTS" for metric_id in expected_metrics
    }
    assert len(domain.upgrade_evidence_requirements) == len(expected_metrics)
    assert sufficiency.blocking_gap_keys == tuple(
        f"financial_temporal:{metric_id}:INSUFFICIENT_COMPARABLE_POINTS"
        for metric_id in sorted(expected_metrics)
    )
