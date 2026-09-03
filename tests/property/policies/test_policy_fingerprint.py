from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, strategies as st

from research_os.policies import (
    PolicyDefinition,
    PolicyOverride,
    PolicyParameter,
    PolicyRegistry,
)


def _definition(policy_id: str, value: Decimal) -> PolicyDefinition:
    return PolicyDefinition(
        policy_id=policy_id,
        policy_version="1.0.0",
        policy_type="thresholds",
        applicability=frozenset({"research"}),
        parameters={
            "threshold": PolicyParameter(
                value=value,
                value_type="decimal",
                unit="ratio",
                minimum=Decimal("0"),
                maximum=Decimal("1"),
            )
        },
        rationale="Fingerprint property fixture",
        source="research_os",
    )


@given(order=st.permutations((0, 1, 2)))
def test_policy_fingerprint_is_independent_of_registration_order(
    order: list[int],
) -> None:
    definitions = (
        _definition("policy:a", Decimal("0.1")),
        _definition("policy:b", Decimal("0.2")),
        _definition("policy:c", Decimal("0.3")),
    )

    registry = PolicyRegistry(tuple(definitions[index] for index in order))

    assert registry.fingerprint == PolicyRegistry(definitions).fingerprint


def test_override_changes_actual_policy_fingerprint_and_snapshot_selection() -> None:
    definition = _definition("policy:a", Decimal("0.1"))
    baseline = PolicyRegistry((definition,))
    overridden = PolicyRegistry(
        (definition,),
        overrides=(
            PolicyOverride(
                policy_id="policy:a",
                base_policy_version="1.0.0",
                operator="analyst:1",
                reason="approved evidence-specific threshold",
                override_ts=datetime(2026, 9, 3, tzinfo=timezone.utc),
                parameters={
                    "threshold": PolicyParameter(
                        value=Decimal("0.15"),
                        value_type="decimal",
                        unit="ratio",
                        minimum=Decimal("0"),
                        maximum=Decimal("1"),
                    )
                },
            ),
        ),
    )

    assert overridden.fingerprint != baseline.fingerprint
    assert (
        overridden.snapshot().policies[0].parameters_fingerprint
        != baseline.snapshot().policies[0].parameters_fingerprint
    )
