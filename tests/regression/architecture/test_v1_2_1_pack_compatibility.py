from datetime import datetime, timezone

from research_os.kpi.distributor import DistributorPack
from research_os.kpi.manufacturing import ManufacturingPack
from research_os.plugins.builtins import DistributorIndustryPlugin, ManufacturingIndustryPlugin
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.runtime.state import ResearchStateView


def _context(facts):
    return ResearchContext(
        run_id="run:pack-compat",
        company=CompanyRef(company_id="synthetic:pack-compat"),
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.3.0",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView([]),
        facts=LegacyFactView(values=facts, evidence_by_fact={}),
        options=ResearchOptions(),
    )


def _plugin_metrics(plugin, facts):
    module = plugin.modules()[0]
    result = module.run(_context(facts), ResearchStateView({}))
    return result.artifacts["kpi.metrics"]


def _assert_metrics_equal(legacy, migrated):
    assert len(migrated) == len(legacy)
    for old, new in zip(legacy, migrated, strict=True):
        assert new.metric_id == old.metric_id
        assert new.value == old.value
        assert new.status == old.status
        assert new.reason_code == old.reason_code
        assert new.formula_version == old.formula_version
        assert new.evidence_ids == old.evidence_ids


def test_distributor_plugin_preserves_v1_2_1_metric_semantics():
    facts = {
        "revenue": 1000.0,
        "cogs": 900.0,
        "avg_ar": 100.0,
        "avg_inventory": 200.0,
        "avg_ap": 150.0,
        "ar": 120.0,
        "inventory": 210.0,
        "ap": 160.0,
        "gross_profit": 100.0,
        "period_type": "H1",
        "period_days": 181,
    }
    legacy = DistributorPack().calculate(facts)
    migrated = _plugin_metrics(DistributorIndustryPlugin(), facts)
    _assert_metrics_equal(legacy, migrated)


def test_manufacturing_plugin_preserves_v1_2_1_metric_semantics():
    facts = {
        "revenue": 1000.0,
        "net_profit_parent": 50.0,
        "assets_begin": 800.0,
        "assets_end": 900.0,
        "equity_begin": 400.0,
        "equity_end": 450.0,
        "ar_begin": 90.0,
        "ar_end": 110.0,
        "inventory_begin": 180.0,
        "inventory_end": 220.0,
        "cogs": 900.0,
        "ocf": 80.0,
        "capex_cash": 20.0,
        "ppe_begin": 200.0,
        "ppe_end": 220.0,
        "period_type": "H1",
        "period_days": 181,
    }
    legacy = ManufacturingPack().calculate(facts)
    migrated = _plugin_metrics(ManufacturingIndustryPlugin(), facts)
    _assert_metrics_equal(legacy, migrated)
