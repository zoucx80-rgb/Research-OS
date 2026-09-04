from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from research_os.application.result import ResearchRunResult
from research_os.completeness.models import MonitoringRule, SensitivityCase
from research_os.contracts.artifact_values import (
    MonitoringPlan,
    SensitivitySet,
)
from research_os.reporting.models import (
    HumanReadableResearchView,
    ResearchReportDocument,
)
from research_os.runtime.core_artifacts import MONITORING_PLAN, SCENARIO_SENSITIVITIES
from research_os.semantics.fingerprint import semantic_fingerprint


class SemanticViolation(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    item_id: str
    field: str


class SemanticPreservationValidation(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["PASS", "FAIL"]
    violations: tuple[SemanticViolation, ...] = Field(default_factory=tuple)
    research_fingerprint: str | None = None
    sensitivity_fingerprint: str | None = None
    monitoring_fingerprint: str | None = None


class SemanticPreservationValidator:
    """Validate semantic qualifiers at domain and reporting boundaries."""

    version = "semantic-preservation@2.0.0"
    _LINEAGE_KEYS = frozenset(
        {
            "evidence_id",
            "evidence_ids",
            "evidence_refs",
            "assumption_id",
            "assumption_ids",
            "assumption_refs",
        }
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
        """Project investor-visible qualifiers without audit-only lineage identifiers."""
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
        return cls._semantic_projection(value)

    @classmethod
    def monitoring_projection(cls, value: Any) -> Any:
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
            value is not None for value in (case.result, case.result_low, case.result_high)
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
        """Retain the pre-2.0 qualifier validator for frozen characterization tests."""
        violations = tuple(
            [violation for case in sensitivities for violation in cls._sensitivity_violations(case)]
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

    @classmethod
    def validate_v2_qualifiers(
        cls,
        *,
        sensitivities: SensitivitySet | None,
        monitoring_plan: MonitoringPlan | None,
    ) -> SemanticPreservationValidation:
        violations: list[SemanticViolation] = []
        if sensitivities is not None:
            for case in sensitivities.cases:
                if case.result is None:
                    continue
                if not case.material_assumptions:
                    violations.append(
                        SemanticViolation(
                            code="SENSITIVITY_ASSUMPTIONS_MISSING",
                            item_id=case.case_key,
                            field="material_assumptions",
                        )
                    )
                if not (case.model_boundary or "").strip():
                    violations.append(
                        SemanticViolation(
                            code="SENSITIVITY_MODEL_BOUNDARY_MISSING",
                            item_id=case.case_key,
                            field="model_boundary",
                        )
                    )
                if not (case.evidence_refs or case.assumption_refs or case.material_assumptions):
                    violations.append(
                        SemanticViolation(
                            code="SENSITIVITY_LINEAGE_MISSING",
                            item_id=case.case_key,
                            field="lineage",
                        )
                    )
        if monitoring_plan is not None:
            for item in monitoring_plan.items:
                if not item.metric_id.strip() or not item.condition.strip():
                    violations.append(
                        SemanticViolation(
                            code="MONITORING_QUALIFIER_MISSING",
                            item_id=item.item_key,
                            field="metric_id/condition",
                        )
                    )
                if not (item.evidence_refs or item.assumption_refs):
                    violations.append(
                        SemanticViolation(
                            code="MONITORING_LINEAGE_MISSING",
                            item_id=item.item_key,
                            field="lineage",
                        )
                    )
        return SemanticPreservationValidation(
            status="FAIL" if violations else "PASS",
            violations=tuple(violations),
            sensitivity_fingerprint=(
                cls.sensitivity_fingerprint(sensitivities) if sensitivities is not None else None
            ),
            monitoring_fingerprint=(
                cls.monitoring_fingerprint(monitoring_plan) if monitoring_plan is not None else None
            ),
        )

    @classmethod
    def validate_reporting_chain(
        cls,
        *,
        result: ResearchRunResult,
        view: HumanReadableResearchView,
        document: ResearchReportDocument,
    ) -> SemanticPreservationValidation:
        if not isinstance(result, ResearchRunResult):
            raise TypeError("result must be ResearchRunResult")
        if not isinstance(view, HumanReadableResearchView):
            raise TypeError("view must be HumanReadableResearchView")
        if not isinstance(document, ResearchReportDocument):
            raise TypeError("document must be ResearchReportDocument")

        expected_fingerprint = semantic_fingerprint(result.artifacts)
        violations: list[SemanticViolation] = []
        if view.semantic_fingerprint != expected_fingerprint:
            violations.append(
                SemanticViolation(
                    code="VIEW_SEMANTIC_FINGERPRINT_MISMATCH",
                    item_id="research-view",
                    field="semantic_fingerprint",
                )
            )
        if document.semantic_fingerprint != expected_fingerprint:
            violations.append(
                SemanticViolation(
                    code="DOCUMENT_SEMANTIC_FINGERPRINT_MISMATCH",
                    item_id="research-document",
                    field="semantic_fingerprint",
                )
            )

        view_by_identity = {
            (item.artifact_id, item.schema_version): item for item in view.artifacts
        }
        audit_by_identity = {
            (item.artifact_id, item.schema_version): item for item in document.audit_appendix
        }
        document_payloads = {
            (item.artifact_id, item.schema_version): item.payload
            for section in document.sections
            for item in section.artifacts
        }
        for envelope in result.artifacts.envelopes():
            identity = (envelope.key.artifact_id, envelope.key.schema_version)
            presented = view_by_identity.get(identity)
            if presented is None:
                violations.append(
                    SemanticViolation(
                        code="VIEW_ARTIFACT_MISSING",
                        item_id=envelope.key.artifact_id,
                        field="artifact",
                    )
                )
                continue
            if (
                presented.type_id != envelope.key.value_type.__qualname__
                or presented.producer_ids != envelope.producer_ids
                or presented.evidence_refs != envelope.evidence_refs
                or presented.value_fingerprint != envelope.value_fingerprint
            ):
                violations.append(
                    SemanticViolation(
                        code="VIEW_ARTIFACT_IDENTITY_MISMATCH",
                        item_id=envelope.key.artifact_id,
                        field="schema/provider/lineage/payload_fingerprint",
                    )
                )
            audit = audit_by_identity.get(identity)
            if audit is None:
                violations.append(
                    SemanticViolation(
                        code="DOCUMENT_AUDIT_LINEAGE_MISSING",
                        item_id=envelope.key.artifact_id,
                        field="audit_appendix",
                    )
                )
            elif (
                audit.type_id != presented.type_id
                or audit.producer_ids != presented.producer_ids
                or audit.evidence_refs != presented.evidence_refs
                or audit.value_fingerprint != presented.value_fingerprint
            ):
                violations.append(
                    SemanticViolation(
                        code="DOCUMENT_AUDIT_LINEAGE_MISMATCH",
                        item_id=envelope.key.artifact_id,
                        field="audit_appendix",
                    )
                )
            if presented.audit_only:
                if identity in document_payloads:
                    violations.append(
                        SemanticViolation(
                            code="AUDIT_ONLY_ARTIFACT_LEAKED_TO_BODY",
                            item_id=envelope.key.artifact_id,
                            field="payload",
                        )
                    )
            elif document_payloads.get(identity) != presented.payload:
                violations.append(
                    SemanticViolation(
                        code="DOCUMENT_ARTIFACT_PAYLOAD_MISMATCH",
                        item_id=envelope.key.artifact_id,
                        field="payload",
                    )
                )

        qualifier_validation = cls.validate_v2_qualifiers(
            sensitivities=result.artifacts.get(SCENARIO_SENSITIVITIES),
            monitoring_plan=result.artifacts.get(MONITORING_PLAN),
        )
        violations.extend(qualifier_validation.violations)
        return SemanticPreservationValidation(
            status="FAIL" if violations else "PASS",
            violations=tuple(violations),
            research_fingerprint=expected_fingerprint,
            sensitivity_fingerprint=qualifier_validation.sensitivity_fingerprint,
            monitoring_fingerprint=qualifier_validation.monitoring_fingerprint,
        )
