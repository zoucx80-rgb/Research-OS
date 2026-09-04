from decimal import Decimal

from research_os.reporting.formatting import HumanValueFormatter


def test_human_value_formatter_handles_financial_units_without_changing_values() -> None:
    formatter = HumanValueFormatter()

    assert formatter.format(Decimal("123456789"), unit="CNY") == "1.23亿元"
    assert formatter.format(Decimal("0.1876"), unit="ratio") == "18.76%"
    assert formatter.format(Decimal("0.034"), unit="pp") == "3.40个百分点"
    assert formatter.format(Decimal("42.5"), unit="days") == "42.50天"
    assert formatter.format(Decimal("18.3"), unit="x") == "18.30倍"
    assert formatter.format(None, unit="CNY") == "—"
