import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pytest

import research_os
from research_os.capital.engine import CapitalEfficiencyEngine
from research_os.completion.gate import REQUIRED_MODULES, ResearchCompletionGate
from research_os.completion.models import ResearchCompletionInput
from research_os.kpi.distributor import DistributorPack
from research_os.plugins.builtins import BuiltinPluginProvider
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolver
from research_os.reporting.summary import DecisionSummaryBuilder
from research_os.router.models import BusinessModelProfile
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.version import RESEARCH_OS_VERSION


def _metric_map(results):
    return {metric.metric_id: metric for metric in results}


def test_h1_balance_flow_arithmetic_uses_h1_period_length():
    metrics = _metric_map(DistributorPack().calculate({
        "avg_ar": 50.0,
        "revenue": 200.0,
        "avg_inventory": 40.0,
        "cogs": 160.0,
        "avg_ap": 20.0,
        "period_type": "H1",
        "period_days": 181,
    }))
    assert metrics["dso_days"].value == pytest.approx(50.0 / 200.0 * 181)
    assert metrics["inventory_turns_period"].value == pytest.approx(4.0)
    assert metrics["inventory_turns_annualized"].value == pytest.approx(4.0 * 365 / 181)


def test_missing_funding_inputs_remain_unknown_not_zero():
    result = CapitalEfficiencyEngine().funding_loop({"operating_cash_flow": -10.0})
    assert result.funding_state == "unknown"
    assert "NEGATIVE_OCF" in result.reason_codes
    assert "DEBT_FUNDS_NWC" not in result.reason_codes


def test_unsupported_primary_model_does_not_get_specialized_kpi_pass():
    profile = BusinessModelProfile(
        company_id="synthetic-consumer",
        primary_model="consumer",
        confidence=0.9,
        evidence_ids=["synthetic-evidence"],
        router_version="router@1.0.0",
    )
    context = ResearchContext(
        run_id="run:correctness:unsupported",
        company=CompanyRef(company_id="synthetic-consumer"),
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            research_os_version="1.4.0",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView([]),
        facts=LegacyFactView(values={}, evidence_by_fact={}),
        options=ResearchOptions(),
    )
    registry = PluginRegistry(core_api_version="1.0", research_os_version="1.4.0")
    for plugin in BuiltinPluginProvider().plugins():
        registry.register(plugin)

    resolution = StrategyResolver().resolve(profile, context, registry)
    assert resolution.industry_plugins == []
    assert any(
        gap.gap_type == "industry_strategy" and gap.business_model == "consumer"
        for gap in resolution.coverage_gaps
    )


def test_reporting_propagates_the_same_completion_result(canonical_report_result_factory):
    statuses = {module: "PASS" for module in REQUIRED_MODULES}
    statuses["Forecast Discipline"] = "NOT_APPLICABLE"
    completion = ResearchCompletionGate().evaluate(
        ResearchCompletionInput(module_statuses=statuses)
    )
    summary = DecisionSummaryBuilder().build(
        canonical_report_result_factory(completion=completion)
    )
    assert summary.final_status == completion.final_status
    assert summary.blocking_modules == completion.blocking_modules
    assert summary.module_statuses == completion.module_statuses


def test_public_and_runtime_version_surfaces_are_equal():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    metadata = json.loads(Path("research_os_version.json").read_text())
    assert RESEARCH_OS_VERSION == "1.2.1"
    assert research_os.__version__ == RESEARCH_OS_VERSION
    assert project["project"]["version"] == RESEARCH_OS_VERSION
    assert metadata["research_os_version"] == RESEARCH_OS_VERSION
