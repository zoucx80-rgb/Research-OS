from pathlib import Path

import pytest

from research_os.reporting import (
    ResearchReportComposer,
    ResearchReportMarkdownRenderer,
    ResearchViewPresenter,
)
from research_os.valuation.reconciliation import ValuationModelRationale


def test_active_reporting_chain_uses_v1_5_12_fingerprints():
    assert ResearchViewPresenter.version == "professional-research-view@1.7.0"
    assert ResearchReportComposer.version == "research-report-composer@1.4.0"
    assert (
        ResearchReportMarkdownRenderer.version
        == "professional-markdown-renderer@1.4.0"
    )


def test_renderer_cannot_import_or_recompute_valuation_reconciliation():
    source = Path(
        "src/research_os/reporting/markdown_renderer_v1_5_12.py"
    ).read_text(encoding="utf-8")

    assert "ValuationReconciler" not in source
    assert "mathematical_intersection" not in source
    assert "cross_check_envelope" not in source


def test_valuation_rationale_rejects_release_or_software_reasons():
    for explanation in (
        "DCF downgraded because Research OS v1.5.12 changed",
        "renderer version cannot display the model",
        "software version limitation",
    ):
        with pytest.raises(ValueError, match="economic rationale"):
            ValuationModelRationale(
                model_id="dcf",
                status="DOWNGRADED",
                economic_factors=("cash_flow_visibility",),
                explanation=explanation,
            )


def test_production_core_has_no_field_company_identity_branches():
    forbidden = ("300034", "钢研高纳")
    offenders = []
    for path in Path("src/research_os").rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for value in forbidden:
            if value in content:
                offenders.append((str(path), value))
    assert offenders == []
