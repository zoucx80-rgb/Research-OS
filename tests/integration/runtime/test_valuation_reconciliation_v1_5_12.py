from research_os.plugins.registry import PluginRegistry
from research_os.router.models import BusinessModelProfile
from research_os.runtime.historical_professional_modules_v1_5_10 import (
    build_professional_builtin_modules_v1_5_10,
)
from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.professional_modules import (
    SemanticValuationModule,
    build_professional_builtin_modules,
)
from research_os.runtime.state import ResearchStateView
from research_os.valuation.reconciliation import ValuationRange


def _ranges():
    return (
        ValuationRange(
            range_id="pe",
            model_id="pe",
            role="model_implied",
            basis="equity_per_share",
            currency="CNY",
            low=12.0,
            high=18.0,
        ),
        ValuationRange(
            range_id="ev-ebitda",
            model_id="ev_ebitda",
            role="model_implied",
            basis="equity_per_share",
            currency="CNY",
            low=15.0,
            high=20.0,
        ),
    )


def test_active_valuation_module_emits_canonical_reconciliation_artifact():
    module = SemanticValuationModule(inputs=ResearchInputs(valuation_ranges=_ranges()))
    state = ResearchStateView(
        {
            "business_model.profile": BusinessModelProfile(
                company_id="synthetic:manufacturer",
                primary_model="manufacturing",
                confidence=0.9,
            ),
            "capital.funding_loop": None,
        }
    )

    result = module.run(None, state)

    reconciliation = result.artifacts["valuation.reconciliation"]
    assert reconciliation.status == "INTERSECTION"
    assert reconciliation.low == 15.0
    assert reconciliation.high == 18.0


def test_current_builder_uses_semantic_valuation_without_mutating_historical_builder():
    registry = PluginRegistry(core_api_version="1.0", research_os_version="1.5.11")
    current = build_professional_builtin_modules(registry=registry, inputs=ResearchInputs())
    historical = build_professional_builtin_modules_v1_5_10(
        registry=registry,
        inputs=ResearchInputs(),
    )

    assert any(isinstance(module, SemanticValuationModule) for module in current)
    assert not any(isinstance(module, SemanticValuationModule) for module in historical)
