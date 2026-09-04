from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


class HumanValueFormatter:
    """Deterministic presentation-only formatting for frozen research values."""

    _RATIO_UNITS = frozenset({"ratio", "percent", "%"})
    _PP_UNITS = frozenset({"pp", "percentage_point", "percentage_points"})
    _DAY_UNITS = frozenset({"day", "days"})
    _MULTIPLE_UNITS = frozenset({"x", "multiple", "times"})

    @staticmethod
    def _decimal(value: int | float | Decimal) -> Decimal:
        try:
            return value if isinstance(value, Decimal) else Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise TypeError(f"unsupported numeric value: {value!r}") from exc

    @staticmethod
    def _fixed(value: Decimal, places: int = 2) -> str:
        quantum = Decimal(1).scaleb(-places)
        return f"{value.quantize(quantum):,.{places}f}"

    def format(
        self,
        value: Any,
        *,
        unit: str | None = None,
        field_name: str | None = None,
    ) -> str:
        if value is None:
            return "—"
        if isinstance(value, bool):
            return "是" if value else "否"
        if not isinstance(value, (int, float, Decimal)):
            return str(value)

        number = self._decimal(value)
        normalized_unit = (unit or "").strip().lower()
        normalized_field = (field_name or "").strip().lower()

        if normalized_unit in {"cny", "rmb", "currency", "cny/share"}:
            suffix = "/股" if normalized_unit == "cny/share" else ""
            absolute = abs(number)
            if absolute >= Decimal("100000000"):
                return f"{self._fixed(number / Decimal('100000000'))}亿元{suffix}"
            if absolute >= Decimal("10000"):
                return f"{self._fixed(number / Decimal('10000'))}万元{suffix}"
            return f"{self._fixed(number)}元{suffix}"
        if normalized_unit in self._RATIO_UNITS:
            return f"{self._fixed(number * Decimal('100'))}%"
        if normalized_unit in self._PP_UNITS:
            return f"{self._fixed(number * Decimal('100'))}个百分点"
        if normalized_unit in self._DAY_UNITS or normalized_field.endswith("_days"):
            return f"{self._fixed(number)}天"
        if normalized_unit in self._MULTIPLE_UNITS:
            return f"{self._fixed(number)}倍"
        if normalized_field in {
            "confidence",
            "usable_evidence_coverage",
            "ambiguity",
            "source_quality",
        }:
            return f"{self._fixed(number * Decimal('100'))}%"
        return self._fixed(number)


def format_cny(value: int | float | Decimal | None) -> str | None:
    """Backward-compatible CNY helper implemented by the deterministic formatter."""

    if value is None:
        return None
    return HumanValueFormatter().format(value, unit="CNY")
