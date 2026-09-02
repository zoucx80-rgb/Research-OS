from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from research_os.application.bootstrap import (
    BootstrapPlanCompiler,
    GitRepositoryAttestor,
    RepositoryAttestation,
    RepositoryAttestor,
    validate_repository_attestation,
)
from research_os.application.command import ResearchRunCommand
from research_os.application.finalizer import RunFinalizer
from research_os.application.plan import ResearchPlanCompiler
from research_os.application.result import (
    ComponentFingerprint,
    ResearchRunResult,
    RunVersionSet,
    VersionIdentity,
)
from research_os.contracts.errors import (
    PersistenceError,
    PluginContractError,
    RepositoryPreflightError,
)
from research_os.plugins.builtins import BuiltinPluginProvider
from research_os.plugins.discovery import discover_plugins
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolution, StrategyResolver
from research_os.plugins.protocols import ResearchPlugin
from research_os.readiness import ResearchReadinessEvaluator
from research_os.release.manifest import CURRENT_RELEASE
from research_os.runtime.core_artifacts import (
    BUSINESS_MODEL_PROFILE,
    KPI_METRICS,
    build_core_artifact_catalog,
)
from research_os.runtime.engine import ResearchEngine, TypedExecutionResult
from research_os.runtime.module_plan import ModulePlan
from research_os.snapshots.service import SnapshotService, UnitOfWorkFactory


def _implementation_files(component: object) -> tuple[tuple[str, Path], ...]:
    implementation_type = type(component)
    source_path = inspect.getsourcefile(implementation_type)
    if source_path is None or not Path(source_path).is_file():
        return ()
    source = Path(source_path).resolve()
    module_parts = implementation_type.__module__.split(".")
    if len(module_parts) == 1:
        return ((source.name, source),)
    package_root = source.parent
    for _ in range(max(len(module_parts) - 2, 0)):
        package_root = package_root.parent
    return tuple(
        (
            f"{module_parts[0]}/{path.relative_to(package_root).as_posix()}",
            path.resolve(),
        )
        for path in sorted(package_root.rglob("*.py"))
        if "__pycache__" not in path.parts
    )


def _implementation_fingerprint(
    component: object | tuple[object, ...], identity: tuple[str, ...]
) -> str:
    components = component if isinstance(component, tuple) else (component,)
    implementation_types = tuple(type(item) for item in components)
    source_files = dict(
        sorted(
            (
                source
                for item in components
                for source in _implementation_files(item)
            ),
            key=lambda item: item[0],
        )
    )
    implementation_parts: list[bytes] = []
    for relative_path, path in source_files.items():
        implementation_parts.extend(
            (relative_path.encode("utf-8"), b"\0", path.read_bytes(), b"\0")
        )
    if not implementation_parts:
        for implementation_type in implementation_types:
            try:
                implementation_parts.extend(
                    (
                        inspect.getsource(implementation_type).encode("utf-8"),
                        b"\0",
                    )
                )
            except (OSError, TypeError) as exc:
                raise RuntimeError(
                    "cannot fingerprint implementation "
                    f"{implementation_type.__qualname__}"
                ) from exc
    identity_bytes = json.dumps(
        (
            *identity,
            *((item.__module__, item.__qualname__) for item in implementation_types),
        ),
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(
        identity_bytes + b"\0" + b"".join(implementation_parts)
    ).hexdigest()


def _plugin_implementation_components(
    plugin: ResearchPlugin, services: object
) -> tuple[object, ...]:
    if services is None:
        raise RuntimeError(f"registered plugin has no services: {plugin.manifest.plugin_id}")
    components: list[object] = [plugin]
    for attribute in (
        "kpi_provider",
        "valuation_methods",
        "forecast_methods",
        "policy_contributions",
        "report_contributions",
    ):
        value = getattr(services, attribute)
        if value is None:
            continue
        if isinstance(value, tuple):
            components.extend(value)
        else:
            components.append(value)
    return tuple(components)


class PluginProvider(Protocol):
    def plugins(self) -> Iterable[ResearchPlugin]: ...


class ResearchApplication:
    def __init__(
        self,
        plugin_providers: tuple[PluginProvider, ...] = (),
        repository_attestor: RepositoryAttestor | None = None,
        unit_of_work_factory: UnitOfWorkFactory | None = None,
        snapshot_service: SnapshotService | None = None,
    ) -> None:
        self._engine = ResearchEngine()
        self._readiness = ResearchReadinessEvaluator()
        self._finalizer = RunFinalizer()
        self._plugin_providers = plugin_providers
        self._repository_attestor = repository_attestor or GitRepositoryAttestor()
        self._unit_of_work_factory = unit_of_work_factory
        self._snapshot_service = snapshot_service or SnapshotService()

    @classmethod
    def build(
        cls,
        *,
        plugin_providers: Iterable[PluginProvider] = (),
        repository_attestor: RepositoryAttestor | None = None,
        unit_of_work_factory: UnitOfWorkFactory | None = None,
        snapshot_service: SnapshotService | None = None,
    ) -> ResearchApplication:
        return cls(
            tuple(plugin_providers),
            repository_attestor,
            unit_of_work_factory,
            snapshot_service,
        )

    def _preflight(self, command: ResearchRunCommand) -> RepositoryAttestation:
        try:
            attestation = self._repository_attestor.attest()
        except RepositoryPreflightError:
            raise
        except Exception as exc:
            raise RepositoryPreflightError(
                "repository attestor failed",
                context={"run_id": command.context.run_id},
            ) from exc
        validate_repository_attestation(command.context, attestation)
        return attestation

    def _registry(self, *, run_id: str) -> PluginRegistry:
        registry = PluginRegistry(
            core_api_version=CURRENT_RELEASE.core_api_version,
            research_os_version=CURRENT_RELEASE.version,
        )
        for provider in (BuiltinPluginProvider(), *self._plugin_providers):
            try:
                plugins = tuple(provider.plugins())
            except Exception as exc:
                raise PluginContractError(
                    "plugin provider failed",
                    context={
                        "provider_type": type(provider).__qualname__,
                        "run_id": run_id,
                    },
                ) from exc
            for plugin in plugins:
                registry.register(plugin)
        discover_plugins(registry)
        return registry

    @staticmethod
    def _metadata(
        command: ResearchRunCommand,
        plans: tuple[ModulePlan, ...],
        strategy: StrategyResolution,
        execution: TypedExecutionResult,
        registry: PluginRegistry,
    ) -> tuple[RunVersionSet, tuple[ComponentFingerprint, ...]]:
        module_versions = tuple(
            sorted(
                (
                    VersionIdentity(
                        component_id=module.spec.module_id,
                        version=module.spec.module_version,
                    )
                    for plan in plans
                    for module in plan.modules
                ),
                key=lambda item: item.component_id,
            )
        )
        resolved_plugins = tuple(
            sorted(
                (*strategy.industry_plugins, *strategy.methodology_plugins),
                key=lambda item: item.plugin_id,
            )
        )
        plugin_versions = tuple(
            VersionIdentity(component_id=item.plugin_id, version=item.plugin_version)
            for item in resolved_plugins
        )
        external = tuple(
            VersionIdentity(component_id=name, version=value)
            for name, value in sorted(
                command.options.external_versions.model_dump().items()
            )
            if value is not None
        )
        metric_versions = tuple(
            VersionIdentity(
                component_id=metric.metric_id,
                version=metric.formula_version,
            )
            for metric in execution.snapshot.require(KPI_METRICS).metrics
        )
        versions = RunVersionSet(
            research_os_version=CURRENT_RELEASE.version,
            core_api_version=CURRENT_RELEASE.core_api_version,
            plugin_api_version=CURRENT_RELEASE.plugin_api_version,
            snapshot_schema_version=CURRENT_RELEASE.snapshot_schema_version,
            http_api_version=CURRENT_RELEASE.http_api_version,
            modules=module_versions,
            plugins=plugin_versions,
            metrics=metric_versions,
            external=external,
        )
        components = tuple(
            sorted(
                (
                    *(
                        ComponentFingerprint(
                            component_id=item.component_id,
                            component_type="module",
                            component_version=item.version,
                            api_version=CURRENT_RELEASE.core_api_version,
                            fingerprint=_implementation_fingerprint(
                                next(
                                    module
                                    for plan in plans
                                    for module in plan.modules
                                    if module.spec.module_id == item.component_id
                                ),
                                (
                                    "module",
                                    item.component_id,
                                    item.version,
                                    CURRENT_RELEASE.core_api_version,
                                ),
                            ),
                        )
                        for item in module_versions
                    ),
                    *(
                        ComponentFingerprint(
                            component_id=item.plugin_id,
                            component_type="plugin",
                            component_version=item.plugin_version,
                            api_version=item.plugin_api_version,
                            fingerprint=_implementation_fingerprint(
                                _plugin_implementation_components(
                                    registry.require(item.plugin_id),
                                    registry.services(item.plugin_id),
                                ),
                                (
                                    "plugin",
                                    item.plugin_id,
                                    item.plugin_version,
                                    item.plugin_api_version,
                                ),
                            ),
                        )
                        for item in resolved_plugins
                    ),
                ),
                key=lambda item: item.component_id,
            )
        )
        return versions, components

    def run(self, command: ResearchRunCommand) -> ResearchRunResult:
        attestation = self._preflight(command)
        catalog = build_core_artifact_catalog()
        registry = self._registry(run_id=command.context.run_id)
        bootstrap_plan = BootstrapPlanCompiler(catalog).compile(
            command,
            attestation=attestation,
        )
        bootstrap = self._engine.execute(bootstrap_plan, command.context, catalog)
        business_model = bootstrap.snapshot.require(BUSINESS_MODEL_PROFILE)
        strategy = StrategyResolver().resolve(
            business_model,
            command.context,
            registry,
            command.options,
        )
        professional_plan = ResearchPlanCompiler(
            catalog,
            registry=registry,
        ).compile(command, bootstrap.snapshot, strategy)
        professional = self._engine.execute(
            professional_plan,
            command.context,
            catalog,
        )
        results = bootstrap.module_results + professional.module_results
        plans = (bootstrap_plan, professional_plan)
        finalized = self._engine.finalize(
            plans=plans,
            execution=TypedExecutionResult(
                snapshot=professional.snapshot,
                module_results=results,
            ),
            catalog=catalog,
            readiness_evaluator=self._readiness,
        )
        versions, components = self._metadata(
            command,
            plans,
            strategy,
            finalized.execution,
            registry,
        )
        result = self._finalizer.finalize(
            command=command,
            execution=finalized.execution,
            strategy=strategy,
            completion=finalized.completion,
            readiness=finalized.readiness,
            versions=versions,
            component_fingerprints=components,
        )
        if not command.options.persist_snapshot:
            return result
        if self._unit_of_work_factory is None:
            raise PersistenceError(
                "snapshot persistence requires a UnitOfWork factory",
                context={"run_id": result.run_id},
            )
        return self._snapshot_service.persist(
            command=command,
            result=result,
            unit_of_work_factory=self._unit_of_work_factory,
        )
