import inspect

from research_os.runtime.builtin_modules import (
    DecisionModule,
    ExpectationModule,
    FinancialSanityModule,
    RepositoryPreflightModule,
    TemporalModule,
    ValuationModule,
    build_builtin_modules,
)


def test_builtin_modules_do_not_accept_legacy_request():
    for cls in (
        RepositoryPreflightModule,
        FinancialSanityModule,
        ExpectationModule,
        ValuationModule,
        DecisionModule,
        TemporalModule,
    ):
        assert "legacy_request" not in inspect.signature(cls.__init__).parameters

    assert "legacy_request" not in inspect.signature(build_builtin_modules).parameters
    assert "inputs" in inspect.signature(build_builtin_modules).parameters
