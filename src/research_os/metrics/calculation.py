from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.metrics import MetricResult
from research_os.contracts.policies import PolicySnapshot
from research_os.contracts.values import Money, Quantity, Ratio
from research_os.metrics.models import MetricDefinition
from research_os.period.resolver import resolve_period_days
from research_os.runtime.context import FactView


class MetricCalculationEngine:
    """Execute centrally registered financial formulas against a bound FactView."""

    def calculate(
        self,
        facts: FactView,
        definition: MetricDefinition,
        policy: PolicySnapshot,
    ) -> MetricResult:
        del policy  # Formula thresholds are introduced through typed policies in M3 Task 3.
        values = facts.as_mapping()
        inputs = tuple(item.fact_id for item in definition.required_inputs)
        references = self._references(facts, inputs)
        missing = tuple(
            item.fact_id
            for item in definition.required_inputs
            if item.required and values.get(item.fact_id) is None
        )
        if missing:
            return self._result(
                facts,
                definition,
                value=None,
                references=references,
                reason_code="MISSING_INPUTS:" + ",".join(sorted(missing)),
            )

        value, reason_code = self._execute(definition.formula_id, values, inputs, facts)
        if value is not None and not references:
            value = None
            reason_code = "MISSING_EVIDENCE"
        return self._result(
            facts,
            definition,
            value=value,
            references=references,
            reason_code=reason_code,
        )

    @staticmethod
    def _references(facts: FactView, inputs: tuple[str, ...]) -> tuple[EvidenceRef, ...]:
        by_identity = {
            (item.evidence_id, item.revision, item.content_fingerprint): item
            for fact_id in inputs
            for item in facts.evidence_refs(fact_id)
        }
        return tuple(by_identity[key] for key in sorted(by_identity))

    @staticmethod
    def _number(value: object) -> Decimal:
        if isinstance(value, Money):
            return value.base_amount
        if isinstance(value, Ratio):
            return value.decimal_value
        if isinstance(value, Quantity):
            return value.value
        if isinstance(value, bool):
            raise ValueError("boolean is not a financial number")
        try:
            resolved = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("metric input is not numeric") from exc
        if not resolved.is_finite():
            raise ValueError("metric input must be finite")
        return resolved

    @classmethod
    def _ratio(cls, numerator: object, denominator: object) -> tuple[Decimal | None, str | None]:
        if isinstance(numerator, Money) and isinstance(denominator, Money):
            numerator._require_same_currency(denominator)
        if isinstance(numerator, Quantity) and isinstance(denominator, Quantity):
            numerator._require_same_unit(denominator)
        den = cls._number(denominator)
        if den == 0:
            return None, "ZERO_DENOMINATOR"
        return cls._number(numerator) / den, None

    @staticmethod
    def _comparison_reason(values: Mapping[str, object], inputs: tuple[str, ...]) -> str | None:
        bases = [values.get(f"{fact_id}_comparison_basis") for fact_id in inputs]
        if any(not isinstance(item, str) or not item.strip() for item in bases):
            return "COMPARISON_BASIS_REQUIRED"
        if len(set(bases)) != 1:
            return "COMPARISON_BASIS_MISMATCH"
        return None

    def _execute(
        self,
        formula_id: str,
        values: Mapping[str, object],
        inputs: tuple[str, ...],
        facts: FactView,
    ) -> tuple[Decimal | None, str | None]:
        raw = tuple(values.get(item) for item in inputs)
        if formula_id == "safe_ratio":
            return self._ratio(raw[0], raw[1])
        if formula_id == "positive_denominator_ratio":
            if self._number(raw[1]) <= 0:
                return None, "NON_POSITIVE_DENOMINATOR"
            return self._ratio(raw[0], raw[1])
        if formula_id == "average_ratio":
            average = (self._number(raw[1]) + self._number(raw[2])) / 2
            return self._ratio(self._number(raw[0]), average)
        if formula_id == "average_to_average_ratio":
            numerator = (self._number(raw[0]) + self._number(raw[1])) / 2
            denominator = (self._number(raw[2]) + self._number(raw[3])) / 2
            return self._ratio(numerator, denominator)
        if formula_id == "difference":
            return self._number(raw[0]) - self._number(raw[1]), None
        if formula_id in {"turnover_days", "average_turnover_days", "cash_conversion_cycle_days", "annualized_ratio"}:
            days = resolve_period_days(facts.reporting_period)
            if days is None:
                return None, "PERIOD_LENGTH_REQUIRED"
            period_days = Decimal(days)
            if formula_id == "turnover_days":
                ratio, reason = self._ratio(raw[0], raw[1])
                return (None, reason) if ratio is None else (ratio * period_days, None)
            if formula_id == "average_turnover_days":
                balance = (self._number(raw[0]) + self._number(raw[1])) / 2
                ratio, reason = self._ratio(balance, raw[2])
                return (None, reason) if ratio is None else (ratio * period_days, None)
            if formula_id == "annualized_ratio":
                ratio, reason = self._ratio(raw[0], raw[1])
                return (None, reason) if ratio is None else (ratio * Decimal(365) / period_days, None)
            dso, dso_reason = self._ratio(raw[0], raw[1])
            dio, dio_reason = self._ratio(raw[2], raw[3])
            dpo, dpo_reason = self._ratio(raw[4], raw[3])
            reason = dso_reason or dio_reason or dpo_reason
            if dso is None or dio is None or dpo is None:
                return None, reason
            return (dso + dio - dpo) * period_days, None
        if formula_id == "working_capital_ratio":
            denominator = self._number(raw[0]) + self._number(raw[1]) - self._number(raw[2])
            return self._ratio(denominator, raw[3])
        if formula_id == "ratio_to_working_capital":
            denominator = self._number(raw[1]) + self._number(raw[2]) - self._number(raw[3])
            return self._ratio(raw[0], denominator)
        if formula_id == "comparable_ratio":
            reason = self._comparison_reason(values, inputs)
            return (None, reason) if reason is not None else self._ratio(raw[0], raw[1])
        if formula_id == "comparable_sum_ratio":
            reason = self._comparison_reason(values, inputs)
            if reason is not None:
                return None, reason
            return self._ratio(self._number(raw[0]) + self._number(raw[1]), raw[2])
        if formula_id == "coalesced_ratio":
            selected_numerator = raw[0] if raw[0] is not None else raw[1]
            if selected_numerator is None:
                return None, "MISSING_INPUTS:factoring_exposure"
            return self._ratio(selected_numerator, raw[2])
        if formula_id == "available_sum_ratio":
            selected_financing = raw[0] if raw[0] is not None else raw[1]
            pieces = (selected_financing, raw[2], raw[3])
            available = tuple(item for item in pieces if item is not None)
            if not available:
                return None, "MISSING_INPUTS:working_capital_financing"
            total_financing = sum(
                (self._number(item) for item in available), Decimal(0)
            )
            return self._ratio(total_financing, raw[4])
        raise ValueError(f"unsupported metric formula: {formula_id}")

    @staticmethod
    def _result(
        facts: FactView,
        definition: MetricDefinition,
        *,
        value: Decimal | None,
        references: tuple[EvidenceRef, ...],
        reason_code: str | None,
    ) -> MetricResult:
        return MetricResult(
            metric_id=definition.metric_id,
            value=value,
            unit=definition.output_unit,
            status="valid" if value is not None else "missing",
            formula_version=f"{definition.formula_id}@{definition.definition_version}",
            reporting_period=facts.reporting_period,
            accounting_scope=facts.accounting_scope,
            evidence_refs=references,
            reason_code=reason_code,
            annualized=definition.annualization_policy == "annualize_365",
        )


__all__ = ["MetricCalculationEngine"]
