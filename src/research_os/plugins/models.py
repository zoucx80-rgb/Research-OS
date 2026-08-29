from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PluginType = Literal["industry", "methodology"]
PluginMaturity = Literal["experimental", "stable"]


class PluginManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    plugin_id: str
    plugin_type: PluginType
    plugin_version: str
    api_version: str
    min_research_os_version: str
    max_research_os_version: str | None = None
    provides: set[str]
    requires: set[str]
    supported_business_models: set[str] = Field(default_factory=set)
    priority: int = 100
    maturity: PluginMaturity = "experimental"

    @field_validator(
        "plugin_id",
        "plugin_version",
        "api_version",
        "min_research_os_version",
    )
    @classmethod
    def _non_empty_identity(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("plugin identity/version fields must be non-empty")
        return value

    @field_validator("max_research_os_version")
    @classmethod
    def _non_empty_optional_version(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("plugin max version must be non-empty when provided")
        return value

    @field_validator("provides", "requires")
    @classmethod
    def _valid_capabilities(cls, values: set[str]) -> set[str]:
        if any(not value.strip() for value in values):
            raise ValueError("capability IDs must be non-empty")
        return values

    @field_validator("supported_business_models")
    @classmethod
    def _valid_business_models(cls, values: set[str]) -> set[str]:
        if any(not value.strip() for value in values):
            raise ValueError("supported business model IDs must be non-empty")
        return values


class ApplicabilityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    applicable: bool
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: list[str] = Field(default_factory=list)


class ResolvedPlugin(BaseModel):
    model_config = ConfigDict(frozen=True)

    plugin_id: str
    plugin_type: PluginType
    plugin_version: str
    api_version: str
    priority: int
    maturity: PluginMaturity
    applicability_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: list[str] = Field(default_factory=list)


class CoverageGap(BaseModel):
    model_config = ConfigDict(frozen=True)

    gap_type: Literal["industry_strategy", "methodology", "capability"]
    business_model: str | None = None
    missing_capability: str | None = None
    reason: str


class ExtensionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    company_id: str
    business_model: str
    coverage_gaps: list[CoverageGap] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    requested_capabilities: list[str] = Field(default_factory=list)
