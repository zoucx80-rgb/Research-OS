import json
import tomllib
from pathlib import Path

import research_os
from research_os.decision.models import DecisionContext, DecisionStateRecord
from research_os.reporting.summary import DecisionSummaryBuilder
from research_os.version import RESEARCH_OS_VERSION


def test_all_runtime_and_public_version_surfaces_are_1_2_1():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    metadata = json.loads(Path("research_os_version.json").read_text())
    assert RESEARCH_OS_VERSION == "1.2.1"
    assert research_os.__version__ == RESEARCH_OS_VERSION
    assert project["project"]["version"] == RESEARCH_OS_VERSION
    assert metadata["research_os_version"] == RESEARCH_OS_VERSION
    assert DecisionContext.model_fields["research_os_version"].default == RESEARCH_OS_VERSION
    assert DecisionStateRecord.model_fields["research_os_version"].default == RESEARCH_OS_VERSION


def test_reporting_default_uses_runtime_version():
    summary = DecisionSummaryBuilder().build({
        "company_id": "synthetic",
        "business_model": "distributor",
        "primary_thesis": "synthetic thesis",
        "thesis_state": "ACTIVE",
        "fundamental_state": "STABLE",
        "expectation_state": "MIXED",
        "valuation_state": "FAIR",
        "evidence_confidence": .8,
        "top_drivers": [],
        "top_risks": [],
        "next_verification_event": "next disclosure",
    })
    assert summary.research_os_version == RESEARCH_OS_VERSION


def test_canonical_runtime_has_no_hardcoded_legacy_version_fallback():
    source = Path("src/research_os/runtime/factory.py").read_text()
    assert '"1.1.0"' not in source
    assert '"1.2.0"' not in source
    assert '"1.2.1"' not in source
    assert "context.baseline.research_os_version" in source
