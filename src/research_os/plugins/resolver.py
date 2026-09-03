from __future__ import annotations

from typing import Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.errors import PluginError
from research_os.plugins.models import (
    ApplicabilityResult,
    CoverageGap,
    PluginManifest,
    ResolvedPlugin,
    SupportAssessment,
)
from research_os.plugins.protocols import IndustryPlugin, MethodologyPlugin, ResearchPlugin
from research_os.plugins.registry import PluginRegistry
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import ResearchContext


class StrategyResolutionError(PluginError):
    code = "PLUGIN_STRATEGY_RESOLUTION_FAILED"


class StrategyOptions(Protocol):
    industry_plugin_override: str | None
    methodology_plugin_overrides: tuple[str, ...]
    override_rationale: str | None
    allow_experimental_plugins: bool


class StrategyResolution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    industry_plugins: tuple[ResolvedPlugin, ...] = Field(default_factory=tuple)
    methodology_plugins: tuple[ResolvedPlugin, ...] = Field(default_factory=tuple)
    coverage_gaps: tuple[CoverageGap, ...] = Field(default_factory=tuple)
    rationale: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)

    @field_validator("evidence_refs")
    @classmethod
    def _canonical_evidence_refs(
        cls, references: tuple[EvidenceRef, ...]
    ) -> tuple[EvidenceRef, ...]:
        by_id: dict[str, EvidenceRef] = {}
        for reference in references:
            existing = by_id.get(reference.evidence_id)
            if existing is not None and existing != reference:
                raise ValueError("strategy lineage has conflicting evidence revisions")
            by_id[reference.evidence_id] = reference
        return tuple(
            sorted(
                by_id.values(),
                key=lambda item: (
                    item.evidence_id,
                    item.revision,
                    item.content_fingerprint,
                ),
            )
        )


class StrategyResolver:
    _BASE_CAPABILITIES = frozenset({"business_model.profile"})

    @staticmethod
    def _applicability(
        plugin: IndustryPlugin,
        context: ResearchContext,
        profile: BusinessModelProfile,
    ) -> ApplicabilityResult:
        try:
            result = plugin.applicability(context, profile)
        except Exception as exc:
            raise StrategyResolutionError(
                f"plugin applicability failed: {plugin.manifest.plugin_id}",
                context={
                    "plugin_id": plugin.manifest.plugin_id,
                    "run_id": context.run_id,
                    "operation": "applicability",
                },
            ) from exc
        if not isinstance(result, ApplicabilityResult):
            raise StrategyResolutionError(
                f"plugin applicability returned invalid type: {plugin.manifest.plugin_id}",
                context={
                    "plugin_id": plugin.manifest.plugin_id,
                    "run_id": context.run_id,
                    "operation": "applicability",
                },
            )
        return result

    @staticmethod
    def _support(
        plugin: MethodologyPlugin,
        context: ResearchContext,
        available_capabilities: frozenset[str],
    ) -> SupportAssessment:
        try:
            result = plugin.supports(context, available_capabilities)
        except Exception as exc:
            raise StrategyResolutionError(
                f"plugin support assessment failed: {plugin.manifest.plugin_id}",
                context={
                    "plugin_id": plugin.manifest.plugin_id,
                    "run_id": context.run_id,
                    "operation": "supports",
                },
            ) from exc
        if not isinstance(result, SupportAssessment):
            raise StrategyResolutionError(
                f"plugin support assessment returned invalid type: {plugin.manifest.plugin_id}",
                context={
                    "plugin_id": plugin.manifest.plugin_id,
                    "run_id": context.run_id,
                    "operation": "supports",
                },
            )
        return result

    @staticmethod
    def _resolved(
        plugin: ResearchPlugin,
        *,
        score: float,
        rationale: tuple[str, ...],
        evidence_refs: tuple[EvidenceRef, ...],
    ) -> ResolvedPlugin:
        manifest = plugin.manifest
        return ResolvedPlugin(
            plugin_id=manifest.plugin_id,
            plugin_type=manifest.plugin_type,
            plugin_version=manifest.plugin_version,
            plugin_api_version=manifest.plugin_api_version,
            priority=manifest.priority,
            maturity=manifest.maturity,
            applicability_score=score,
            rationale=rationale,
            evidence_refs=evidence_refs,
        )

    @staticmethod
    def _eligible_maturity(options: StrategyOptions, manifest: PluginManifest) -> bool:
        return manifest.maturity == "stable" or options.allow_experimental_plugins

    @staticmethod
    def _business_model_gap(profile: BusinessModelProfile) -> CoverageGap | None:
        if profile.primary_model != "unknown":
            return None
        if profile.classification_status == "UNSUPPORTED_TAXONOMY":
            return CoverageGap(
                gap_type="business_model_taxonomy",
                business_model="unknown",
                reason="business description is meaningful but no supported business-model taxonomy matched",
                reason_code="UNSUPPORTED_BUSINESS_MODEL_TAXONOMY",
                affected_capabilities=("industry_strategy",),
                fallback_available=True,
            )
        if profile.classification_status == "INSUFFICIENT_EVIDENCE":
            return CoverageGap(
                gap_type="business_model_evidence",
                business_model="unknown",
                reason="insufficient usable evidence to classify the primary business model",
                reason_code="INSUFFICIENT_BUSINESS_MODEL_EVIDENCE",
                affected_capabilities=("industry_strategy",),
                fallback_available=True,
            )
        if profile.classification_status == "UNRESOLVED":
            return CoverageGap(
                gap_type="business_model_ambiguity",
                business_model="unknown",
                reason="top business-model candidates are inside the policy gap",
                reason_code="BUSINESS_MODEL_UNRESOLVED",
                affected_capabilities=("industry_strategy",),
                fallback_available=True,
            )
        return None

    def _automatic_industry_for_profile(
        self,
        profile: BusinessModelProfile,
        context: ResearchContext,
        registry: PluginRegistry,
        options: StrategyOptions,
    ) -> tuple[IndustryPlugin, ApplicabilityResult] | None:
        candidates: list[tuple[float, int, str, IndustryPlugin, ApplicabilityResult]] = []
        for manifest in registry.manifests("industry"):
            if profile.primary_model not in manifest.supported_business_models:
                continue
            if not self._eligible_maturity(options, manifest):
                continue
            registered = registry.get(manifest.plugin_id)
            if registered is None:
                continue
            plugin = cast(IndustryPlugin, registered)
            applicability = self._applicability(plugin, context, profile)
            if not applicability.applicable:
                continue
            candidates.append(
                (
                    -applicability.rule_score,
                    manifest.priority,
                    manifest.plugin_id,
                    plugin,
                    applicability,
                )
            )
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        return candidates[0][3], candidates[0][4]

    def _override_industry(
        self,
        profile: BusinessModelProfile,
        context: ResearchContext,
        registry: PluginRegistry,
        options: StrategyOptions,
    ) -> tuple[IndustryPlugin, ApplicabilityResult] | None:
        plugin_id = options.industry_plugin_override
        if plugin_id is None:
            return None
        registered = registry.get(plugin_id)
        if registered is None:
            raise StrategyResolutionError(
                f"industry override plugin is not registered: {plugin_id}",
                context={"plugin_id": plugin_id, "run_id": context.run_id},
            )
        plugin = cast(IndustryPlugin, registered)
        manifest = plugin.manifest
        if manifest.plugin_type != "industry":
            raise StrategyResolutionError(
                f"industry override is not an industry plugin: {plugin_id}",
                context={"plugin_id": plugin_id, "run_id": context.run_id},
            )
        if profile.primary_model not in manifest.supported_business_models:
            raise StrategyResolutionError(
                f"industry override {plugin_id} does not support {profile.primary_model}",
                context={"plugin_id": plugin_id, "run_id": context.run_id},
            )
        if not self._eligible_maturity(options, manifest):
            raise StrategyResolutionError(
                f"experimental industry override {plugin_id} requires explicit experimental opt-in",
                context={"plugin_id": plugin_id, "run_id": context.run_id},
            )
        applicability = self._applicability(plugin, context, profile)
        if not applicability.applicable:
            raise StrategyResolutionError(
                f"industry override {plugin_id} is not applicable to the current profile",
                context={"plugin_id": plugin_id, "run_id": context.run_id},
            )
        return plugin, applicability

    def resolve(
        self,
        profile: BusinessModelProfile,
        context: ResearchContext,
        registry: PluginRegistry,
        options: StrategyOptions,
    ) -> StrategyResolution:
        industry: list[ResolvedPlugin] = []
        methodology: list[ResolvedPlugin] = []
        gaps: list[CoverageGap] = []
        rationale: list[str] = []
        evidence_refs = list(profile.evidence_refs)

        model_gap = self._business_model_gap(profile)
        if model_gap is not None:
            gaps.append(model_gap)
            rationale.append(f"business model unresolved: {model_gap.reason_code}")
        else:
            override = self._override_industry(profile, context, registry, options)
            if override is not None:
                plugin, applicability = override
                evidence_refs.extend(applicability.evidence_refs)
                industry.append(
                    self._resolved(
                        plugin,
                        score=applicability.rule_score,
                        rationale=applicability.rationale,
                        evidence_refs=applicability.evidence_refs,
                    )
                )
                rationale.append(
                    f"industry override {plugin.manifest.plugin_id}: {options.override_rationale}"
                )
            else:
                choice = self._automatic_industry_for_profile(profile, context, registry, options)
                if choice is None:
                    gaps.append(
                        CoverageGap(
                            gap_type="industry_strategy",
                            business_model=profile.primary_model,
                            reason="no compatible industry strategy plugin for primary business model",
                            reason_code="NO_COMPATIBLE_INDUSTRY_PLUGIN",
                            affected_capabilities=("industry_strategy",),
                            fallback_available=True,
                        )
                    )
                else:
                    plugin, applicability = choice
                    evidence_refs.extend(applicability.evidence_refs)
                    industry.append(
                        self._resolved(
                            plugin,
                            score=applicability.rule_score,
                            rationale=applicability.rationale,
                            evidence_refs=applicability.evidence_refs,
                        )
                    )
                    rationale.append(
                        f"auto-selected {plugin.manifest.plugin_id} for primary business model {profile.primary_model}"
                    )

        for secondary_model in profile.secondary_models:
            secondary_profile = profile.model_copy(
                update={"primary_model": secondary_model, "secondary_models": []}
            )
            choice = self._automatic_industry_for_profile(
                secondary_profile, context, registry, options
            )
            if choice is None:
                gaps.append(
                    CoverageGap(
                        gap_type="industry_strategy",
                        business_model=secondary_model,
                        reason="no compatible industry strategy plugin for secondary business model",
                        reason_code="NO_COMPATIBLE_INDUSTRY_PLUGIN",
                        affected_capabilities=("industry_strategy",),
                        fallback_available=True,
                    )
                )
            else:
                plugin, applicability = choice
                evidence_refs.extend(applicability.evidence_refs)
                rationale.append(
                    f"compatible secondary industry plugin {plugin.manifest.plugin_id} retained as coverage metadata only"
                )
        if profile.secondary_models:
            rationale.append(
                "secondary business models retained as classification and coverage metadata; canonical industry strategy follows primary model only"
            )

        available_capabilities = set(self._BASE_CAPABILITIES)
        for resolved in industry:
            registered = registry.get(resolved.plugin_id)
            if registered is None:
                raise StrategyResolutionError(
                    f"resolved plugin is no longer registered: {resolved.plugin_id}",
                    context={
                        "plugin_id": resolved.plugin_id,
                        "run_id": context.run_id,
                    },
                )
            plugin = cast(IndustryPlugin, registered)
            available_capabilities.update(plugin.manifest.service_capabilities)

        explicit_methodology = set(options.methodology_plugin_overrides)
        for manifest in registry.manifests("methodology"):
            if not self._eligible_maturity(options, manifest):
                continue
            if explicit_methodology and manifest.plugin_id not in explicit_methodology:
                continue
            registered = registry.get(manifest.plugin_id)
            if registered is None:
                continue
            methodology_plugin = cast(MethodologyPlugin, registered)
            support = self._support(methodology_plugin, context, frozenset(available_capabilities))
            if not support.supported:
                continue
            evidence_refs.extend(support.evidence_refs)
            methodology.append(
                self._resolved(
                    methodology_plugin,
                    score=1.0,
                    rationale=support.rationale,
                    evidence_refs=support.evidence_refs,
                )
            )
            available_capabilities.update(manifest.service_capabilities)
            rationale.append(f"selected methodology {manifest.plugin_id}")

        missing_explicit = explicit_methodology - {item.plugin_id for item in methodology}
        for plugin_id in sorted(missing_explicit):
            gaps.append(
                CoverageGap(
                    gap_type="methodology",
                    missing_capability=plugin_id,
                    reason="explicit methodology override could not be satisfied",
                )
            )
        if explicit_methodology:
            rationale.append(f"methodology override: {options.override_rationale}")

        return StrategyResolution(
            industry_plugins=tuple(industry),
            methodology_plugins=tuple(methodology),
            coverage_gaps=tuple(gaps),
            rationale=tuple(rationale),
            evidence_refs=tuple(evidence_refs),
        )
