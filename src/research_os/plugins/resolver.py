from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from research_os.plugins.models import CoverageGap, ResolvedPlugin
from research_os.plugins.registry import PluginRegistry
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import ResearchContext
from research_os.runtime.state import ResearchStateView


class StrategyResolutionError(ValueError):
    pass


class StrategyResolution(BaseModel):
    model_config = ConfigDict(frozen=True)

    industry_plugins: list[ResolvedPlugin] = Field(default_factory=list)
    methodology_plugins: list[ResolvedPlugin] = Field(default_factory=list)
    coverage_gaps: list[CoverageGap] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class StrategyResolver:
    _BASE_CAPABILITIES = {"business_model.profile"}

    @staticmethod
    def _resolved(plugin, *, score: float, rationale: list[str]) -> ResolvedPlugin:
        manifest = plugin.manifest
        return ResolvedPlugin(
            plugin_id=manifest.plugin_id,
            plugin_type=manifest.plugin_type,
            plugin_version=manifest.plugin_version,
            api_version=manifest.api_version,
            priority=manifest.priority,
            maturity=manifest.maturity,
            applicability_score=score,
            rationale=list(rationale),
        )

    @staticmethod
    def _eligible_maturity(context: ResearchContext, manifest) -> bool:
        return manifest.maturity == "stable" or context.options.allow_experimental_plugins

    def _automatic_industry_for_model(
        self,
        model: str,
        context: ResearchContext,
        registry: PluginRegistry,
    ):
        candidates = []
        for manifest in registry.manifests("industry"):
            if model not in manifest.supported_business_models:
                continue
            if not self._eligible_maturity(context, manifest):
                continue
            if not manifest.requires.issubset(self._BASE_CAPABILITIES):
                continue
            plugin = registry.get(manifest.plugin_id)
            applicability = plugin.applicability(context)
            if not applicability.applicable:
                continue
            candidates.append((
                -applicability.score,
                manifest.priority,
                manifest.plugin_id,
                plugin,
                applicability,
            ))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        return candidates[0][3], candidates[0][4]

    def _override_industry(
        self,
        profile: BusinessModelProfile,
        context: ResearchContext,
        registry: PluginRegistry,
    ):
        plugin_id = context.options.industry_plugin_override
        if plugin_id is None:
            return None
        plugin = registry.get(plugin_id)
        if plugin is None:
            raise StrategyResolutionError(f"industry override plugin is not registered: {plugin_id}")
        manifest = plugin.manifest
        if manifest.plugin_type != "industry":
            raise StrategyResolutionError(f"industry override is not an industry plugin: {plugin_id}")
        if profile.primary_model not in manifest.supported_business_models:
            raise StrategyResolutionError(
                f"industry override {plugin_id} does not support {profile.primary_model}"
            )
        if not self._eligible_maturity(context, manifest):
            raise StrategyResolutionError(
                f"experimental industry override {plugin_id} requires explicit experimental opt-in"
            )
        return plugin, plugin.applicability(context)

    def resolve(
        self,
        profile: BusinessModelProfile,
        context: ResearchContext,
        registry: PluginRegistry,
    ) -> StrategyResolution:
        industry: list[ResolvedPlugin] = []
        methodology: list[ResolvedPlugin] = []
        gaps: list[CoverageGap] = []
        rationale: list[str] = []
        selected_ids: set[str] = set()

        override = self._override_industry(profile, context, registry)
        if override is not None:
            plugin, applicability = override
            industry.append(
                self._resolved(
                    plugin,
                    score=applicability.score,
                    rationale=applicability.rationale,
                )
            )
            selected_ids.add(plugin.manifest.plugin_id)
            rationale.append(
                f"industry override {plugin.manifest.plugin_id}: {context.options.override_rationale}"
            )
        else:
            requested_models = [profile.primary_model, *profile.secondary_models]
            for index, model in enumerate(requested_models):
                choice = self._automatic_industry_for_model(model, context, registry)
                if choice is None:
                    gaps.append(
                        CoverageGap(
                            gap_type="industry_strategy",
                            business_model=model,
                            reason=(
                                "no compatible industry strategy plugin for primary business model"
                                if index == 0
                                else "no compatible industry strategy plugin for secondary business model"
                            ),
                        )
                    )
                    continue
                plugin, applicability = choice
                if plugin.manifest.plugin_id in selected_ids:
                    continue
                industry.append(
                    self._resolved(
                        plugin,
                        score=applicability.score,
                        rationale=applicability.rationale,
                    )
                )
                selected_ids.add(plugin.manifest.plugin_id)
                rationale.append(
                    f"auto-selected {plugin.manifest.plugin_id} for business model {model}"
                )

        available_capabilities = set(self._BASE_CAPABILITIES)
        for resolved in industry:
            plugin = registry.get(resolved.plugin_id)
            available_capabilities.update(plugin.manifest.provides)

        planning_artifacts = {capability: None for capability in available_capabilities}
        planning_artifacts["business_model.profile"] = profile
        planning_state = ResearchStateView(planning_artifacts)

        explicit_methodology = set(context.options.methodology_plugin_overrides)
        for manifest in registry.manifests("methodology"):
            if not self._eligible_maturity(context, manifest):
                continue
            if explicit_methodology and manifest.plugin_id not in explicit_methodology:
                continue
            if not manifest.requires.issubset(available_capabilities):
                continue
            plugin = registry.get(manifest.plugin_id)
            if not plugin.supports(context, planning_state):
                continue
            methodology.append(
                self._resolved(plugin, score=1.0, rationale=["methodology supports context"])
            )
            available_capabilities.update(manifest.provides)
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
            rationale.append(f"methodology override: {context.options.override_rationale}")

        return StrategyResolution(
            industry_plugins=industry,
            methodology_plugins=methodology,
            coverage_gaps=gaps,
            rationale=rationale,
        )
