from __future__ import annotations

from decimal import Decimal
from functools import total_ordering
import re
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_os.period.models import ReportingPeriod


_CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")


class _DecimalValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("*", mode="after", check_fields=False)
    @classmethod
    def _finite_decimal_fields(cls, value: object) -> object:
        if isinstance(value, Decimal) and not value.is_finite():
            raise ValueError("financial values must be finite")
        return value


@total_ordering
class Money(_DecimalValue):
    amount: Decimal
    currency: str
    scale: int = Field(default=1, gt=0)

    @field_validator("currency")
    @classmethod
    def _currency_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not _CURRENCY_CODE.fullmatch(normalized):
            raise ValueError("currency must be a three-letter code")
        return normalized

    @property
    def base_amount(self) -> Decimal:
        return self.amount * Decimal(self.scale)

    def _require_same_currency(self, other: object) -> Money:
        if not isinstance(other, Money):
            raise TypeError("money operations require another Money value")
        if self.currency != other.currency:
            raise ValueError(
                f"currency mismatch: {self.currency} != {other.currency}"
            )
        return other

    def __add__(self, other: object) -> Money:
        resolved = self._require_same_currency(other)
        return Money(
            amount=(self.base_amount + resolved.base_amount) / Decimal(self.scale),
            currency=self.currency,
            scale=self.scale,
        )

    def __sub__(self, other: object) -> Money:
        resolved = self._require_same_currency(other)
        return Money(
            amount=(self.base_amount - resolved.base_amount) / Decimal(self.scale),
            currency=self.currency,
            scale=self.scale,
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Money)
            and self.currency == other.currency
            and self.base_amount == other.base_amount
        )

    def __lt__(self, other: object) -> bool:
        resolved = self._require_same_currency(other)
        return self.base_amount < resolved.base_amount


@total_ordering
class Ratio(_DecimalValue):
    value: Decimal
    representation: Literal["decimal", "percent", "basis_points"] = "decimal"

    @property
    def decimal_value(self) -> Decimal:
        divisor = {
            "decimal": Decimal(1),
            "percent": Decimal(100),
            "basis_points": Decimal(10_000),
        }[self.representation]
        return self.value / divisor

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Ratio) and self.decimal_value == other.decimal_value

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Ratio):
            raise TypeError("ratio comparisons require another Ratio value")
        return self.decimal_value < other.decimal_value


@total_ordering
class Quantity(_DecimalValue):
    value: Decimal
    unit: str

    @field_validator("unit")
    @classmethod
    def _unit_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("unit must be non-empty")
        return normalized

    def _require_same_unit(self, other: object) -> Quantity:
        if not isinstance(other, Quantity):
            raise TypeError("quantity operations require another Quantity value")
        if self.unit != other.unit:
            raise ValueError(f"unit mismatch: {self.unit} != {other.unit}")
        return other

    def __add__(self, other: object) -> Quantity:
        resolved = self._require_same_unit(other)
        return Quantity(value=self.value + resolved.value, unit=self.unit)

    def __sub__(self, other: object) -> Quantity:
        resolved = self._require_same_unit(other)
        return Quantity(value=self.value - resolved.value, unit=self.unit)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Quantity)
            and self.unit == other.unit
            and self.value == other.value
        )

    def __lt__(self, other: object) -> bool:
        resolved = self._require_same_unit(other)
        return self.value < resolved.value


class AccountingScope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    accounting_standard: str | None = None
    consolidation: Literal["consolidated", "standalone", "unknown"] = "unknown"
    segment: str | None = None
    geography: str | None = None
    continuing_operations: bool | None = None

    @field_validator("accounting_standard", "segment", "geography")
    @classmethod
    def _non_empty_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("accounting scope dimensions must be non-empty")
        return normalized

    def is_comparable_with(self, other: AccountingScope) -> bool:
        if not isinstance(other, AccountingScope):
            return False
        return self == other

    def require_comparable(self, other: AccountingScope) -> None:
        if not self.is_comparable_with(other):
            raise ValueError("accounting scope mismatch")

    @classmethod
    def from_facts(cls, facts: Mapping[str, Any]) -> AccountingScope:
        raw = facts.get("accounting_scope")
        if isinstance(raw, cls):
            return raw
        if isinstance(raw, Mapping):
            return cls.model_validate(dict(raw))
        return cls(
            accounting_standard=facts.get("accounting_standard"),
            consolidation=facts.get("consolidation") or "unknown",
            segment=facts.get("segment"),
            geography=facts.get("geography"),
            continuing_operations=facts.get("continuing_operations"),
        )


FinancialValue = Money | Ratio | Quantity


__all__ = [
    "AccountingScope",
    "FinancialValue",
    "Money",
    "Quantity",
    "Ratio",
    "ReportingPeriod",
]
