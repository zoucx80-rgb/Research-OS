from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import cast

from pydantic import BaseModel, JsonValue

from research_os.application.result import ResearchRunResult

from .fingerprint import semantic_fingerprint
from .models import HumanReadableResearchView, PresentedArtifact


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reporting requires timezone-aware datetimes")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return _json_value(value.value)
    if isinstance(value, BaseModel):
        return cast(
            JsonValue,
            {
                field_name: _json_value(getattr(value, field_name))
                for field_name in type(value).model_fields
            },
        )
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("reporting mappings require string keys")
        return cast(JsonValue, {key: _json_value(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return cast(JsonValue, [_json_value(item) for item in value])
    if isinstance(value, (set, frozenset)):
        items = [_json_value(item) for item in value]
        return cast(JsonValue, sorted(items, key=lambda item: str(item)))
    raise TypeError(f"cannot project {type(value).__name__} into reporting JSON")


class ResearchViewPresenter:
    """Project a frozen Core API 2.0 result without re-running research semantics."""

    version = "professional-research-view@2.0.0"

    def present(self, result: ResearchRunResult) -> HumanReadableResearchView:
        if not isinstance(result, ResearchRunResult):
            raise TypeError("ResearchViewPresenter.present requires ResearchRunResult")
        artifacts = tuple(
            PresentedArtifact(
                artifact_id=envelope.key.artifact_id,
                schema_version=envelope.key.schema_version,
                type_id=envelope.key.value_type.__qualname__,
                producer_ids=envelope.producer_ids,
                evidence_refs=envelope.evidence_refs,
                value_fingerprint=envelope.value_fingerprint,
                payload=_json_value(envelope.value),
            )
            for envelope in result.artifacts.envelopes()
        )
        return HumanReadableResearchView(
            company_id=result.company.company_id,
            decision_ts=result.decision_ts,
            baseline=result.baseline,
            versions=result.versions,
            execution_completion=result.execution_completion.final_status,
            research_readiness=result.research_readiness.final_status,
            semantic_fingerprint=semantic_fingerprint(result.artifacts),
            artifacts=artifacts,
        )
