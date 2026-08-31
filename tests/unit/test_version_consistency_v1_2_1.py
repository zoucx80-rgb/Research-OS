import json
from pathlib import Path

import research_os
from research_os.decision.models import DecisionContext, DecisionStateRecord
from research_os.release.manifest import CURRENT_RELEASE
from research_os.reporting.summary import DecisionSummaryBuilder
from research_os.version import RESEARCH_OS_VERSION


def test_runtime_version_defaults_follow_canonical_release_manifest():
    metadata = json.loads(Path("research_os_version.json").read_text())
    assert research_os.__version__ == CURRENT_RELEASE.version == RESEARCH_OS_VERSION
    assert metadata == CURRENT_RELEASE.to_public_metadata()
    assert DecisionContext.model_fields["research_os_version"].default == RESEARCH_OS_VERSION
    assert DecisionStateRecord.model_fields["research_os_version"].default == RESEARCH_OS_VERSION


def test_reporting_uses_canonical_run_version(canonical_report_result_factory):
    summary = DecisionSummaryBuilder().build(canonical_report_result_factory())
    assert summary.research_os_version == RESEARCH_OS_VERSION


def test_canonical_runtime_has_no_hardcoded_legacy_version_fallback():
    source = Path("src/research_os/runtime/factory.py").read_text()
    assert '"1.1.0"' not in source
    assert '"1.2.0"' not in source
    assert '"1.2.1"' not in source
    assert "context.baseline.research_os_version" in source
