from research_os.runtime.factory import ResearchRuntime, ResearchRuntimeFactory


def test_default_factory_returns_independent_runtime_instances():
    first = ResearchRuntimeFactory.default()
    second = ResearchRuntimeFactory.default()

    assert isinstance(first, ResearchRuntime)
    assert isinstance(second, ResearchRuntime)
    assert first is not second


def test_factory_has_explicit_provider_extension_point():
    assert callable(ResearchRuntimeFactory.with_providers)
