from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field

from research_os.reporting.research_view_v1_5_11 import (
    HumanReadableResearchView as _PreviousResearchView,
    ResearchViewPresenter as _PreviousPresenter,
)
from research_os.runtime.result import ResearchRunResult
from research_os.semantics.preservation import SemanticPreservationValidator


class HumanReadableResearchView(_PreviousResearchView):
    model_config = ConfigDict(frozen=True)

    valuation_reconciliation: dict[str, Any] | None = None
    valuation_model_rationales: list[dict[str, Any]] = Field(default_factory=list)
    semantic_preservation: dict[str, Any] | None = None
    cycle_assessment: dict[str, Any] | None = None
    moat_assessment: dict[str, Any] | None = None
    presentation_version: str = "professional-research-view@1.7.0"


class ResearchViewPresenter(_PreviousPresenter):
    """v1.5.12 projection that rejects qualifier loss before composition."""

    version = "professional-research-view@1.7.0"

    @staticmethod
    def _status(value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, "status"):
            return str(value.status)
        if isinstance(value, dict):
            status = value.get("status")
            return str(status) if status is not None else None
        return None

    @staticmethod
    def _violation_codes(value: Any) -> list[str]:
        violations = getattr(value, "violations", None)
        if violations is None and isinstance(value, dict):
            violations = value.get("violations")
        codes: list[str] = []
        for item in violations or []:
            code = getattr(item, "code", None)
            if code is None and isinstance(item, dict):
                code = item.get("code")
            if code:
                codes.append(str(code))
        return codes

    @staticmethod
    def _fingerprint(value: Any, field: str) -> str | None:
        if value is None:
            return None
        if hasattr(value, field):
            return getattr(value, field)
        if isinstance(value, dict):
            candidate = value.get(field)
            return str(candidate) if candidate is not None else None
        return None

    def build(
        self,
        result: ResearchRunResult,
        locale: str = _PreviousPresenter._SUPPORTED_LOCALE,
    ) -> HumanReadableResearchView:
        validation = result.artifacts.get("validation.semantic_preservation")
        if self._status(validation) == "FAIL":
            detail = ", ".join(self._violation_codes(validation)) or "unknown violation"
            raise ValueError(f"semantic preservation validation failed: {detail}")

        previous = super().build(result, locale=locale)
        sensitivity = previous.research_completeness.get("scenario.sensitivities")
        monitoring = previous.research_completeness.get("monitoring.rules")
        has_sensitivity = sensitivity not in (None, [], (), {})
        has_monitoring = monitoring not in (None, [], (), {})
        if (has_sensitivity or has_monitoring) and self._status(validation) != "PASS":
            raise ValueError(
                "semantic preservation validation is required for protected payloads"
            )

        expected_sensitivity = self._fingerprint(
            validation, "sensitivity_fingerprint"
        )
        if has_sensitivity:
            if expected_sensitivity is None:
                raise ValueError("sensitivity semantic fingerprint is required")
            actual_sensitivity = SemanticPreservationValidator.sensitivity_fingerprint(
                sensitivity
            )
            if actual_sensitivity != expected_sensitivity:
                raise ValueError("view sensitivity semantic fingerprint mismatch")

        expected_monitoring = self._fingerprint(validation, "monitoring_fingerprint")
        if has_monitoring:
            if expected_monitoring is None:
                raise ValueError("monitoring semantic fingerprint is required")
            actual_monitoring = SemanticPreservationValidator.monitoring_fingerprint(
                monitoring
            )
            if actual_monitoring != expected_monitoring:
                raise ValueError("view monitoring semantic fingerprint mismatch")

        data = previous.model_dump(mode="python")
        reconciliation = result.artifacts.get("valuation.reconciliation")
        rationales = result.artifacts.get("valuation.rationales")
        preservation = result.artifacts.get("semantic.preservation")
        cycle = result.artifacts.get("semantic.cycle_assessment")
        moat = result.artifacts.get("semantic.moat_assessment")
        data.update(
            valuation_reconciliation=self._project(reconciliation),
            valuation_model_rationales=self._project(rationales) or [],
            semantic_preservation=self._project(preservation),
            cycle_assessment=self._project(cycle),
            moat_assessment=self._project(moat),
            presentation_version=self.version,
        )
        return HumanReadableResearchView.model_validate(data)
