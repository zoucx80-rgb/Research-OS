from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope, ReportingPeriod


MetricKind = Literal["balance", "flow", "ratio", "delta", "growth", "statistical"]
MetricStatus = Literal["valid", "missing", "invalid", "not_applicable"]


class MetricDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric_id: str
    definition_version: str
    output_kind: MetricKind
    output_unit: str

    @field_validator("metric_id", "definition_version", "output_unit")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("metric definition identity fields must be non-empty")
        return value


class MetricResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric_id: str
    value: Decimal | float | int | None
    unit: str | None = None
    status: MetricStatus
    formula_version: str
    reporting_period: ReportingPeriod
    accounting_scope: AccountingScope
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    reason_code: str | None = None
    annualized: bool | None = None

    @field_validator("metric_id", "formula_version")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("metric result identity fields must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_missingness_and_lineage(self) -> MetricResult:
        if self.status == "valid" and self.value is None:
            raise ValueError("valid metric requires a value")
        if self.status != "valid" and self.value is not None:
            raise ValueError("non-valid metric cannot carry a value")
        if self.status == "valid" and not self.evidence_refs:
            raise ValueError("valid metric requires EvidenceRef lineage")

        by_evidence_id: dict[str, EvidenceRef] = {}
        for reference in self.evidence_refs:
            current = by_evidence_id.get(reference.evidence_id)
            if current is not None and current != reference:
                raise ValueError(
                    f"metric lineage has conflicting revisions for {reference.evidence_id}"
                )
            by_evidence_id[reference.evidence_id] = reference
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(
                sorted(
                    by_evidence_id.values(),
                    key=lambda item: (
                        item.evidence_id,
                        item.revision,
                        item.content_fingerprint,
                    ),
                )
            ),
        )
        return self


class MetricSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    metrics: tuple[MetricResult, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _sort_and_reject_duplicates(self) -> MetricSet:
        metric_ids = [item.metric_id for item in self.metrics]
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("metric set contains duplicate metric_id values")
        object.__setattr__(
            self,
            "metrics",
            tuple(sorted(self.metrics, key=lambda item: item.metric_id)),
        )
        return self
