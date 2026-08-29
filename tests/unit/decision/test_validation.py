import importlib
import importlib.util

import pytest


def _load(name: str):
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, f"missing required module {name}"
    return importlib.import_module(name)


def test_neutral_is_not_a_legal_research_decision_state():
    m = _load("research_os.decision.validation")
    with pytest.raises(ValueError):
        m.validate_decision_state("NEUTRAL")


def test_existing_decision_state_is_accepted():
    m = _load("research_os.decision.validation")
    assert m.validate_decision_state("WAIT_FOR_CONFIRMATION") == "WAIT_FOR_CONFIRMATION"
