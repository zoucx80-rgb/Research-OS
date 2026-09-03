from research_os.valuation.fitness import ModelFitnessInputs
from research_os.valuation.router import ValuationContext, ValuationRouter


def f(**kw):
    d = dict(
        data_quality=0.9,
        earnings_stability=0.8,
        cash_flow_visibility=0.8,
        capital_structure_fit=0.8,
        business_model_fit=0.8,
        forecast_stability=0.8,
    )
    d.update(kw)
    return ModelFitnessInputs(**d)


def test_distributor_with_volatile_fcf_does_not_use_dcf_as_primary():
    r = ValuationRouter().route(
        ValuationContext(
            business_model="distributor",
            models={
                "dcf": f(cash_flow_visibility=0.2),
                "pe": f(),
                "pb": f(capital_structure_fit=0.9),
            },
        )
    )
    assert r.models["dcf"].status != "PRIMARY"
    assert "arithmetic_average_target" not in r.model_dump()


def test_low_fitness_model_cannot_dominate_primary_models():
    r = ValuationRouter().route(
        ValuationContext(
            business_model="manufacturing",
            models={"dcf": f(data_quality=0.2), "ev_ebitda": f(), "pe": f()},
        )
    )
    assert "dcf" not in r.primary_models
