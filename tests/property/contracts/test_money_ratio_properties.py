from __future__ import annotations

from decimal import Decimal

from hypothesis import given, strategies as st

from research_os.contracts.values import Money, Ratio


finite_decimals = st.decimals(
    min_value=Decimal("-1000000"),
    max_value=Decimal("1000000"),
    allow_nan=False,
    allow_infinity=False,
    places=6,
)
positive_scales = st.integers(min_value=1, max_value=1_000_000_000)


@given(amount=finite_decimals, scale=positive_scales)
def test_money_base_amount_round_trips_through_any_positive_scale(
    amount: Decimal, scale: int
) -> None:
    value = Money(amount=amount, currency="CNY", scale=scale)

    assert value.base_amount / Decimal(scale) == amount


@given(left=finite_decimals, right=finite_decimals, scale=positive_scales)
def test_money_addition_preserves_exact_base_amount(
    left: Decimal, right: Decimal, scale: int
) -> None:
    result = Money(amount=left, currency="CNY", scale=scale) + Money(
        amount=right,
        currency="CNY",
        scale=scale,
    )

    assert result.base_amount == (left + right) * Decimal(scale)


@given(value=finite_decimals)
def test_ratio_representations_have_the_same_economic_value(value: Decimal) -> None:
    decimal = Ratio(value=value, representation="decimal")
    percent = Ratio(value=value * 100, representation="percent")
    basis_points = Ratio(value=value * 10_000, representation="basis_points")

    assert decimal == percent == basis_points
