from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field

from research_os.reporting.research_view_v1_5_09 import (
    HumanReadableResearchView as _PreviousResearchView,
    ResearchViewPresenter as _PreviousPresenter,
)
from research_os.runtime.result import ResearchRunResult


class HumanReadableResearchView(_PreviousResearchView):
    model_config = ConfigDict(frozen=True)

    research_completeness: dict[str, Any] = Field(default_factory=dict)
    presentation_version: str = "professional-research-view@1.5.0"


class ResearchViewPresenter(_PreviousPresenter):
    """v1.5.10 additive human projection of canonical completeness artifacts."""

    version = "professional-research-view@1.5.0"

    _ARTIFACTS = (
        "research.operating_evidence",
        "financial.time_series",
        "cash_flow.quality_bridge",
        "expectation.consensus_distribution",
        "peers.comparables",
        "scenario.sensitivities",
        "monitoring.rules",
        "monitoring.verification_calendar",
        "monitoring.prior_run_review",
        "methodology.disclosure",
    )

    @classmethod
    def _project(cls, value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="python")
        if isinstance(value, tuple):
            return [cls._project(item) for item in value]
        if isinstance(value, list):
            return [cls._project(item) for item in value]
        if isinstance(value, dict):
            return {key: cls._project(item) for key, item in value.items()}
        return value

    def build(
        self,
        result: ResearchRunResult,
        locale: str = _PreviousPresenter._SUPPORTED_LOCALE,
    ) -> HumanReadableResearchView:
        previous = super().build(result, locale=locale)
        data = previous.model_dump(mode="python")
        projected = {
            artifact_id: self._project(result.artifacts[artifact_id])
            for artifact_id in self._ARTIFACTS
            if artifact_id in result.artifacts and result.artifacts[artifact_id] not in (None, [], (), {})
        }
        data.update(
            research_completeness=projected,
            presentation_version=self.version,
        )
        return HumanReadableResearchView.model_validate(data)
