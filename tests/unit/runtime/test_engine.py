from datetime import datetime, timezone

import pytest

from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.runtime.engine import (
    ModuleExecutionError,
    PipelineDefinitionError,
    ResearchEngine,
)
from research_os.runtime.modules import ModuleResult, ModuleSpec
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


def _context() -> ResearchContext:
    return ResearchContext(
        run_id="run:engine",
        company=CompanyRef(company_id="synthetic:engine"),
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version=RESEARCH_OS_VERSION,
            core_api_version=CORE_API_VERSION,
        ),
        evidence=LegacyEvidenceView([]),
        facts=LegacyFactView(values={}, evidence_by_fact={}),
        options=ResearchOptions(),
    )


class FakeModule:
    def __init__(self, module_id, requires, provides, calls=None, artifacts=None, error=None):
        self.spec = ModuleSpec(
            module_id=module_id,
            module_version="1.0.0",
            requires=set(requires),
            provides=set(provides),
        )
        self.calls = calls
        self.artifacts = artifacts
        self.error = error

    def run(self, context, state):
        if self.calls is not None:
            self.calls.append(self.spec.module_id)
        if self.error is not None:
            raise self.error
        artifacts = self.artifacts
        if artifacts is None:
            artifacts = {cap: self.spec.module_id for cap in self.spec.provides}
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS",
            artifacts=artifacts,
            evidence_ids=[],
            diagnostics=[],
        )


def test_engine_orders_modules_by_capability_dependencies_deterministically():
    calls = []
    modules = [
        FakeModule("b", {"a.ready"}, {"b.ready"}, calls),
        FakeModule("c", set(), {"c.ready"}, calls),
        FakeModule("a", set(), {"a.ready"}, calls),
    ]

    result = ResearchEngine(modules).run(_context())

    assert calls == ["a", "b", "c"]
    assert result.module_results["b"].status == "PASS"
    assert result.get("b.ready") == "b"


def test_engine_rejects_missing_required_capability_before_execution():
    with pytest.raises(PipelineDefinitionError, match="missing"):
        ResearchEngine([FakeModule("a", {"missing"}, {"a.ready"})]).run(_context())


def test_engine_rejects_dependency_cycle_before_execution():
    modules = [
        FakeModule("a", {"b.ready"}, {"a.ready"}),
        FakeModule("b", {"a.ready"}, {"b.ready"}),
    ]
    with pytest.raises(PipelineDefinitionError, match="cycle"):
        ResearchEngine(modules).run(_context())


def test_engine_rejects_duplicate_capability_provider():
    modules = [
        FakeModule("a", set(), {"business_model.primary"}),
        FakeModule("b", set(), {"business_model.primary"}),
    ]
    with pytest.raises(PipelineDefinitionError, match="business_model.primary"):
        ResearchEngine(modules).run(_context())


def test_engine_rejects_undeclared_artifact_from_module():
    module = FakeModule(
        "a",
        set(),
        {"a.ready"},
        artifacts={"undeclared": True},
    )
    with pytest.raises(PipelineDefinitionError, match="undeclared"):
        ResearchEngine([module]).run(_context())


def test_engine_wraps_module_exception_with_module_identity():
    module = FakeModule("broken", set(), {"done"}, error=RuntimeError("boom"))
    with pytest.raises(ModuleExecutionError, match="broken") as exc_info:
        ResearchEngine([module]).run(_context())
    assert isinstance(exc_info.value.__cause__, RuntimeError)
