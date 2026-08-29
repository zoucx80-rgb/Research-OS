import importlib.util

import research_os.kpi.base as kpi_base
from research_os.runtime import ResearchRuntime, ResearchRuntimeFactory


def test_canonical_runtime_is_the_only_research_orchestration_policy_surface():
    runtime = ResearchRuntimeFactory.default()
    assert isinstance(runtime, ResearchRuntime)
    assert importlib.util.find_spec("research_os.orchestration") is None


def test_kpi_base_does_not_expose_a_second_registry_or_resolution_policy():
    assert not hasattr(kpi_base, "KpiPackRegistry")
    assert not hasattr(kpi_base, "KpiPackResolution")
