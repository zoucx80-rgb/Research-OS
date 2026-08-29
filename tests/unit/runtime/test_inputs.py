from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from research_os.runtime.inputs import ResearchInputs


def test_research_inputs_is_immutable_and_uses_safe_defaults():
    inputs = ResearchInputs()

    assert inputs.financial_unit == "元"
    assert inputs.financial_observations == ()
    assert inputs.valuation_models == {}
    assert inputs.claimed_conclusions == ()
    assert inputs.versions == {}
    assert inputs.fundamental_state == "UNCERTAIN"
    assert inputs.valuation_state == "UNRELIABLE"
    assert inputs.expectation_state == "MIXED"

    with pytest.raises(ValidationError):
        inputs.financial_unit = "亿元"


def test_research_inputs_defensively_copies_mutable_inputs():
    versions = {"research_os_version": "1.4.0"}
    inputs = ResearchInputs(versions=versions)
    versions["research_os_version"] = "corrupted"

    assert inputs.versions["research_os_version"] == "1.4.0"
