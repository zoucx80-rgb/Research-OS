from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from research_os.contracts.artifact_values import AssumptionRef
from research_os.contracts.evidence import EvidenceRef


ValuationSupportStatus = Literal[
    "SUPPORTED",
    "CONDITIONALLY_SUPPORTED",
    "SANITY_CHECK_ONLY",
    "CONTRAINDICATED",
    "INSUFFICIENT_EVIDENCE",
]


class ValuationSupportAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    method_id: str
    status: ValuationSupportStatus
    reason_codes: tuple[str, ...] = Field(min_length=1)
    rationale: str

    @field_validator("rationale")
    @classmethod
    def _economic_rationale_only(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("valuation rationale must be non-empty")
        if re.search(r"research\s*os|software|release|renderer|v?\d+\.\d+\.\d+", normalized, re.IGNORECASE):
            raise ValueError("software or version metadata is not an economic rationale")
        return normalized


class ValuationMethodInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    currency: str
    basis: str
    valuation_date: date
    values: Mapping[str, object]
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    assumption_refs: tuple[AssumptionRef, ...] = Field(default_factory=tuple)

    @field_validator("currency", "basis")
    @classmethod
    def _identity_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("valuation currency and basis must be non-empty")
        return normalized.upper() if len(normalized) == 3 else normalized

    @field_validator("values")
    @classmethod
    def _freeze_values(cls, value: Mapping[str, object]) -> Mapping[str, object]:
        return MappingProxyType(dict(value))

    @field_serializer("values")
    def _serialize_values(self, value: Mapping[str, object]) -> dict[str, object]:
        return dict(value)


class SensitivityPoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    parameter: str
    input_value: Decimal
    result: Decimal


class ValuationMethodResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    method_id: str
    status: Literal["SUPPORTED", "INSUFFICIENT_EVIDENCE"]
    currency: str
    basis: str
    valuation_date: date
    bear_case: Decimal | None = None
    base_case: Decimal | None = None
    bull_case: Decimal | None = None
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    assumption_refs: tuple[AssumptionRef, ...] = Field(default_factory=tuple)
    sensitivities: tuple[SensitivityPoint, ...] = Field(default_factory=tuple)
    limitations: tuple[str, ...] = Field(default_factory=tuple)


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("boolean is not a valuation input")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("valuation input is not numeric") from exc
    if not result.is_finite():
        raise ValueError("valuation inputs must be finite")
    return result


class _BaseMethod:
    method_id: str
    required_inputs: tuple[str, ...]

    def _missing(self, inputs: ValuationMethodInput) -> tuple[str, ...]:
        return tuple(key for key in self.required_inputs if inputs.values.get(key) is None)

    def _insufficient(
        self, inputs: ValuationMethodInput, missing: tuple[str, ...]
    ) -> ValuationMethodResult:
        return ValuationMethodResult(
            method_id=self.method_id,
            status="INSUFFICIENT_EVIDENCE",
            currency=inputs.currency,
            basis=inputs.basis,
            valuation_date=inputs.valuation_date,
            evidence_refs=inputs.evidence_refs,
            assumption_refs=inputs.assumption_refs,
            limitations=("missing required inputs: " + ", ".join(missing),),
        )


class PEMethod(_BaseMethod):
    method_id = "pe"
    required_inputs = ("eps", "multiple")

    def execute(self, inputs: ValuationMethodInput) -> ValuationMethodResult:
        if missing := self._missing(inputs):
            return self._insufficient(inputs, missing)
        eps = _decimal(inputs.values["eps"])
        multiple = _decimal(inputs.values["multiple"])
        base = eps * multiple
        bear_multiple = _decimal(inputs.values.get("bear_multiple", multiple))
        bull_multiple = _decimal(inputs.values.get("bull_multiple", multiple))
        return ValuationMethodResult(
            method_id=self.method_id,
            status="SUPPORTED",
            currency=inputs.currency,
            basis=inputs.basis,
            valuation_date=inputs.valuation_date,
            bear_case=eps * bear_multiple,
            base_case=base,
            bull_case=eps * bull_multiple,
            evidence_refs=inputs.evidence_refs,
            assumption_refs=inputs.assumption_refs,
            sensitivities=(
                SensitivityPoint(parameter="multiple", input_value=bear_multiple, result=eps * bear_multiple),
                SensitivityPoint(parameter="multiple", input_value=multiple, result=base),
                SensitivityPoint(parameter="multiple", input_value=bull_multiple, result=eps * bull_multiple),
            ),
        )


class PBMethod(_BaseMethod):
    method_id = "pb"
    required_inputs = ("book_value_per_share", "multiple")

    def execute(self, inputs: ValuationMethodInput) -> ValuationMethodResult:
        if missing := self._missing(inputs):
            return self._insufficient(inputs, missing)
        book = _decimal(inputs.values["book_value_per_share"])
        multiple = _decimal(inputs.values["multiple"])
        result = book * multiple
        return ValuationMethodResult(method_id=self.method_id, status="SUPPORTED", currency=inputs.currency, basis=inputs.basis, valuation_date=inputs.valuation_date, bear_case=result, base_case=result, bull_case=result, evidence_refs=inputs.evidence_refs, assumption_refs=inputs.assumption_refs)


class DCFMethod(_BaseMethod):
    method_id = "dcf"
    required_inputs = ("cash_flows", "discount_rate", "terminal_value")

    def execute(self, inputs: ValuationMethodInput) -> ValuationMethodResult:
        if missing := self._missing(inputs):
            return self._insufficient(inputs, missing)
        raw_cash_flows = inputs.values["cash_flows"]
        if not isinstance(raw_cash_flows, Sequence) or isinstance(
            raw_cash_flows, (str, bytes)
        ):
            return self._insufficient(inputs, ("cash_flows sequence",))
        cash_flows = tuple(_decimal(value) for value in raw_cash_flows)
        if not cash_flows:
            return self._insufficient(inputs, ("non-empty cash_flows",))
        rate = _decimal(inputs.values["discount_rate"])
        if rate <= -1:
            return self._insufficient(inputs, ("valid discount_rate",))
        terminal = _decimal(inputs.values["terminal_value"])
        base = sum(
            (cash_flow / ((Decimal(1) + rate) ** period) for period, cash_flow in enumerate(cash_flows, start=1)),
            Decimal(0),
        )
        base += terminal / ((Decimal(1) + rate) ** max(len(cash_flows), 1))
        return ValuationMethodResult(method_id=self.method_id, status="SUPPORTED", currency=inputs.currency, basis=inputs.basis, valuation_date=inputs.valuation_date, base_case=base, evidence_refs=inputs.evidence_refs, assumption_refs=inputs.assumption_refs, limitations=("bear and bull cases require explicit scenario inputs",))


class SOTPMethod(_BaseMethod):
    method_id = "sotp"
    required_inputs = ("parts",)

    def execute(self, inputs: ValuationMethodInput) -> ValuationMethodResult:
        if missing := self._missing(inputs):
            return self._insufficient(inputs, missing)
        parts = inputs.values["parts"]
        if isinstance(parts, Mapping):
            values = tuple(parts.values())
        elif isinstance(parts, Sequence) and not isinstance(parts, (str, bytes)):
            values = tuple(parts)
        else:
            return self._insufficient(inputs, ("parts mapping or sequence",))
        if not values:
            return self._insufficient(inputs, ("non-empty parts",))
        base = sum((_decimal(value) for value in values), Decimal(0))
        return ValuationMethodResult(method_id=self.method_id, status="SUPPORTED", currency=inputs.currency, basis=inputs.basis, valuation_date=inputs.valuation_date, base_case=base, evidence_refs=inputs.evidence_refs, assumption_refs=inputs.assumption_refs, limitations=("segment values require consistent basis and valuation date",))


__all__ = ["DCFMethod", "PBMethod", "PEMethod", "SOTPMethod", "SensitivityPoint", "ValuationMethodInput", "ValuationMethodResult", "ValuationSupportAssessment", "ValuationSupportStatus"]
