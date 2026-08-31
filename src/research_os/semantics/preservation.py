from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from research_os.completeness.models import MonitoringRule, SensitivityCase


class SemanticViolation(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    item_id: str
    field: str


class SemanticPreservationValidation(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["PASS", "FAIL"]
    violations: tuple[SemanticViolation, ...] = Field(default_factory=tuple)
    sensitivity_fingerprint: str | None = None
    monitoring_fingerprint: str | None = None


class SemanticPreservationValidator:
    """Validate inseparable qualifiers before presentation sees an artifact."""

    _LINEAGE_KEYS = frozenset(
        {"evidence_id", "evidence_ids", "assumption_id", "assumption_ids"}
    )

    @classmethod
    def _normalized(cls, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return cls._normalized(value.model_dump(mode="python"))
        if isinstance(value, dict):
            return {
                str(key): cls._normalized(item)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        if isinstance(value, (list, tuple)):
            return [cls._normalized(item) for item in value]
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        return value

    @classmethod
    def fingerprint(cls, value: Any) -> str:
        payload = json.dumps(
            cls._normalized(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(payload).hexdigest()

    @classmethod
    def _semantic_projection(cls, value: Any) -> Any:
        """Project the investor-visible semantic payload without audit-only lineage."""

        if isinstance(value, BaseModel):
            value = value.model_dump(mode="python")
        if isinstance(value, dict):
            return {
                str(key): cls._semantic_projection(item)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
                if str(key) not in cls._LINEAGE_KEYS
            }
        if isinstance(value, (list, tuple)):
            return [cls._semantic_projection(item) for item in value]
        return cls._normalized(value)

    @classmethod
    def sensitivity_projection(cls, value: Any) -> Any:
        """Canonical result-plus-qualifier projection at every reporting boundary."""

        return cls._semantic_projection(value)

    @classmethod
    def monitoring_projection(cls, value: Any) -> Any:
        """Canonical rule projection; calendar events are independently presentational."""

        if isinstance(value, BaseModel):
            value = value.model_dump(mode="python")
        if isinstance(value, dict) and "rules" in value:
            value = value.get("rules") or []
        return cls._semantic_projection(value)

    @classmethod
    def sensitivity_fingerprint(cls, value: Any) -> str:
        return cls.fingerprint(cls.sensitivity_projection(value))

    @classmethod
    def monitoring_fingerprint(cls, value: Any) -> str:
        return cls.fingerprint(cls.monitoring_projection(value))

    @staticmethod
    def _sensitivity_violations(case: SensitivityCase) -> list[SemanticViolation]:
        has_result = any(
            value is not None
            for value in (case.result, case.result_low, case.result_high)
        )
        if not has_result:
            return []
        missing = []
        if not case.material_assumptions:
            missing.append(("SENSITIVITY_ASSUMPTIONS_MISSING", "material_assumptions"))
        if not (case.model_boundary or "").strip():
            missing.append(("SENSITIVITY_MODEL_BOUNDARY_MISSING", "model_boundary"))
        if not (case.applicability or "").strip():
            missing.append(("SENSITIVITY_APPLICABILITY_MISSING", "applicability"))
        return [
            SemanticViolation(code=code, item_id=case.case_id, field=field)
            for code, field in missing
        ]

    @staticmethod
    def _monitoring_violations(rule: MonitoringRule) -> list[SemanticViolation]:
        missing = []
        if rule.threshold_type is None:
            missing.append(("THRESHOLD_TYPE_MISSING", "threshold_type"))
        if not (rule.threshold_source or "").strip():
            missing.append(("THRESHOLD_SOURCE_MISSING", "threshold_source"))
        if not (rule.comparison_basis or "").strip():
            missing.append(("THRESHOLD_COMPARISON_BASIS_MISSING", "comparison_basis"))
        if not (rule.applicability or "").strip():
            missing.append(("THRESHOLD_APPLICABILITY_MISSING", "applicability"))
        return [
            SemanticViolation(code=code, item_id=rule.rule_id, field=field)
            for code, field in missing
        ]

    @classmethod
    def validate(
        cls,
        *,
        sensitivities: tuple[SensitivityCase, ...],
        monitoring_rules: tuple[MonitoringRule, ...],
    ) -> SemanticPreservationValidation:
        violations = tuple(
            [
                violation
                for case in sensitivities
                for violation in cls._sensitivity_violations(case)
            ]
            + [
                violation
                for rule in monitoring_rules
                for violation in cls._monitoring_violations(rule)
            ]
        )
        return SemanticPreservationValidation(
            status="FAIL" if violations else "PASS",
            violations=violations,
            sensitivity_fingerprint=(
                cls.sensitivity_fingerprint(sensitivities) if sensitivities else None
            ),
            monitoring_fingerprint=(
                cls.monitoring_fingerprint(monitoring_rules) if monitoring_rules else None
            ),
        )
