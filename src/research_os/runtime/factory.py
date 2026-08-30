from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from research_os.completion.gate import REQUIRED_MODULES, ResearchCompletionGate
from research_os.completion.models import ResearchCompletionInput
from research_os.plugins.builtins import BuiltinPluginProvider
from research_os.plugins.registry import PluginRegistry
from research_os.runtime.builtin_modules import build_builtin_modules
from research_os.runtime.context import ResearchContext
from research_os.runtime.engine import ResearchEngine
from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.result import ComponentFingerprint, ResearchRunResult
from research_os.snapshots.service import SnapshotService


@runtime_checkable
class PluginProvider(Protocol):
    """Trusted source of fresh plugin objects for one runtime composition."""

    def plugins(self) -> list[Any]: ...


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(item) for item in value)
    return value


class ResearchRuntime:
    """Canonical, run-scoped composition and execution boundary.

    The runtime owns composition policy, completion, fingerprinting and snapshot
    freezing. ResearchEngine stays unaware of plugin identities and industries.
    Registries and module instances are rebuilt for every run so plugins cannot
    leak mutable state across research runs.
    """

    def __init__(
        self,
        *,
        providers: Iterable[PluginProvider],
        completion_gate: ResearchCompletionGate | None = None,
        snapshot_service: SnapshotService | None = None,
    ):
        self._providers = tuple(providers)
        self._completion_gate = completion_gate or ResearchCompletionGate()
        self._snapshots = snapshot_service or SnapshotService()

    def _build_registry(self, context: ResearchContext) -> PluginRegistry:
        registry = PluginRegistry(
            core_api_version=context.baseline.core_api_version,
            research_os_version=context.baseline.research_os_version,
        )
        for provider in self._providers:
            plugins = provider.plugins()
            for plugin in plugins:
                registry.register(plugin)
        return registry

    @staticmethod
    def _completion_statuses(state, inputs: ResearchInputs) -> dict[str, str]:
        statuses = {name: "INSUFFICIENT_EVIDENCE" for name in REQUIRED_MODULES}
        results = state.module_results
        artifacts = state.artifacts

        preflight = results.get("core:repository-preflight")
        if preflight is not None:
            statuses["Repository Preflight"] = preflight.status

        pit = results.get("core:pit-lineage")
        if pit is not None:
            statuses["PIT Validation"] = (
                "PASS" if artifacts.get("evidence.pit") else pit.status
            )
            lineage = artifacts.get("validation.lineage") or {}
            statuses["Evidence Lineage"] = lineage.get("status", pit.status)

        direct = {
            "core:financial-sanity": "Financial Sanity",
            "core:business-model": "Business Model Router",
            "core:industry-kpi": "KPI Pack",
            "core:capital-efficiency": "Capital Efficiency",
            "core:funding-loop": "Funding Loop",
            "core:expectation": "Expectation Evidence",
            "core:forecast-discipline": "Forecast Discipline",
            "core:decision": "Decision State",
        }
        for module_id, completion_name in direct.items():
            result = results.get(module_id)
            if result is not None:
                statuses[completion_name] = result.status

        driver = results.get("core:driver-thesis")
        if driver is not None:
            drivers = artifacts.get("drivers.graph")
            theses = list(artifacts.get("thesis.items") or [])
            statuses["Driver Graph"] = "PASS" if drivers is not None else driver.status
            statuses["Thesis"] = "PASS" if theses else driver.status
            statuses["Anti-Thesis"] = (
                "PASS"
                if theses and all(getattr(item, "anti_thesis", None) for item in theses)
                else "INSUFFICIENT_EVIDENCE"
            )
            statuses["Falsifiers"] = (
                "PASS"
                if theses and any(getattr(item, "falsifiers", None) for item in theses)
                else "INSUFFICIENT_EVIDENCE"
            )

        valuation = results.get("core:valuation")
        if valuation is not None:
            routing = artifacts.get("valuation.routing")
            if valuation.status == "FAIL":
                statuses["Valuation Fitness"] = "FAIL"
            elif routing is not None and getattr(routing, "primary_models", None):
                statuses["Valuation Fitness"] = "PASS"
            else:
                statuses["Valuation Fitness"] = "INSUFFICIENT_EVIDENCE"
            statuses["Valuation Execution"] = (
                valuation.status
                if inputs.valuation_execution is not None
                else "INSUFFICIENT_EVIDENCE"
            )

        temporal = results.get("core:temporal")
        if temporal is not None:
            if inputs.next_verification_event is None:
                statuses["Next Verification Event"] = "INSUFFICIENT_EVIDENCE"
                statuses["Temporal Consistency"] = "INSUFFICIENT_EVIDENCE"
            else:
                statuses["Next Verification Event"] = temporal.status
                statuses["Temporal Consistency"] = temporal.status

        return statuses

    @staticmethod
    def _fingerprints(modules, strategy_resolution) -> list[ComponentFingerprint]:
        fingerprints = [
            ComponentFingerprint(
                component_id=module.spec.module_id,
                component_type="module",
                component_version=module.spec.module_version,
                api_version="1.0",
            )
            for module in modules
        ]
        if strategy_resolution is not None:
            for plugin in [
                *strategy_resolution.industry_plugins,
                *strategy_resolution.methodology_plugins,
            ]:
                fingerprints.append(
                    ComponentFingerprint(
                        component_id=plugin.plugin_id,
                        component_type=f"plugin:{plugin.plugin_type}",
                        component_version=plugin.plugin_version,
                        api_version=plugin.api_version,
                    )
                )
        return sorted(
            fingerprints,
            key=lambda item: (
                item.component_type,
                item.component_id,
                item.component_version,
                item.api_version or "",
            ),
        )

    @staticmethod
    def _report_contributions(registry: PluginRegistry, strategy_resolution) -> list[Any]:
        contributions: list[Any] = []
        if strategy_resolution is None:
            return contributions
        for resolved in strategy_resolution.industry_plugins:
            plugin = registry.get(resolved.plugin_id)
            if plugin is None:
                continue
            contributions.extend(list(plugin.report_contributions() or []))
        return sorted(
            contributions,
            key=lambda item: (
                getattr(item, "order", 0),
                getattr(item, "contribution_id", ""),
            ),
        )

    @staticmethod
    def _version_bundle(
        context: ResearchContext,
        inputs: ResearchInputs,
        strategy_resolution,
        business_model,
    ) -> dict[str, str]:
        supplied = dict(inputs.versions)
        selected_plugins = []
        if strategy_resolution is not None:
            selected_plugins = [
                f"{item.plugin_id}@{item.plugin_version}"
                for item in strategy_resolution.industry_plugins
            ]
        return {
            "research_os_version": context.baseline.research_os_version,
            "dataset_version": supplied.get("dataset_version", "unspecified"),
            "parser_version": supplied.get("parser_version", "unspecified"),
            "formula_version": supplied.get("formula_version", "runtime-managed"),
            "router_version": supplied.get(
                "router_version",
                getattr(business_model, "router_version", "unspecified"),
            ),
            "kpi_pack_version": supplied.get(
                "kpi_pack_version",
                ",".join(selected_plugins) if selected_plugins else "none",
            ),
            "driver_model_version": supplied.get(
                "driver_model_version", "core:driver-thesis@1.0.0"
            ),
            "forecast_version": supplied.get("forecast_version", "none"),
            "valuation_version": supplied.get(
                "valuation_version", "core:valuation@1.0.0"
            ),
            "report_version": supplied.get("report_version", "semantic-report@1.0.0"),
            "core_api_version": context.baseline.core_api_version,
        }

    def run_context(
        self,
        context: ResearchContext,
        inputs: ResearchInputs | None = None,
    ) -> ResearchRunResult:
        run_inputs = inputs or ResearchInputs()
        registry = self._build_registry(context)
        modules = build_builtin_modules(registry=registry, inputs=run_inputs)
        state = ResearchEngine(modules).run(context)

        business_model = state.get("business_model.profile")
        strategy_resolution = state.get("strategy.resolution")
        if business_model is None:
            raise RuntimeError("canonical runtime requires a business model result")
        if strategy_resolution is None:
            raise RuntimeError("canonical runtime requires a strategy resolution result")

        statuses = self._completion_statuses(state, run_inputs)
        completion = self._completion_gate.evaluate(
            ResearchCompletionInput(
                module_statuses=statuses,
                tool_completed=True,
                claimed_conclusions=list(run_inputs.claimed_conclusions),
            )
        )
        fingerprints = self._fingerprints(modules, strategy_resolution)
        module_results = dict(state.module_results)
        artifacts = dict(state.artifacts)
        artifacts["report.contributions"] = self._report_contributions(
            registry,
            strategy_resolution,
        )

        payload = {
            "run_id": context.run_id,
            "company": context.company.model_dump(mode="json"),
            "decision_ts": context.decision_ts.isoformat(),
            "business_model": business_model.model_dump(mode="json"),
            "module_results": {
                module_id: _jsonable(result)
                for module_id, result in sorted(module_results.items())
            },
            "artifacts": _jsonable(artifacts),
            "completion": completion.model_dump(mode="json"),
        }
        snapshot = self._snapshots.freeze(
            context.company.company_id,
            context.decision_ts,
            self._version_bundle(
                context,
                run_inputs,
                strategy_resolution,
                business_model,
            ),
            payload=payload,
            component_fingerprints=fingerprints,
            strategy_resolution=strategy_resolution,
        )

        return ResearchRunResult(
            run_id=context.run_id,
            company=context.company,
            decision_ts=context.decision_ts,
            baseline=context.baseline,
            business_model=business_model,
            strategy_resolution=strategy_resolution,
            module_results=module_results,
            artifacts=artifacts,
            completion=completion,
            component_fingerprints=fingerprints,
            snapshot=snapshot,
        )


class ResearchRuntimeFactory:
    """Composition root with an explicit provider extension point."""

    @classmethod
    def default(cls) -> ResearchRuntime:
        return ResearchRuntime(providers=(BuiltinPluginProvider(),))

    @classmethod
    def with_providers(cls, *providers: PluginProvider) -> ResearchRuntime:
        return ResearchRuntime(providers=providers)
