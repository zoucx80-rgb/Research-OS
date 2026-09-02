from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from research_os.contracts.artifacts import (
    ArtifactCatalog,
    ArtifactDefinition,
    ArtifactKey,
    ArtifactMode,
    ArtifactStore,
    ArtifactWrite,
)
from research_os.runtime.engine import (
    ModuleExecutionError,
    PipelineDefinitionError,
    ResearchEngine,
)
from research_os.runtime.module_plan import ModulePlanCompiler
from research_os.runtime.modules import ModuleResult, ModuleSpec


@dataclass
class TypedModule:
    spec: ModuleSpec
    result: ModuleResult

    def run(self, context: object, state: object) -> ModuleResult:
        return self.result


@dataclass
class ReadingTypedModule:
    spec: ModuleSpec
    required_key: ArtifactKey[str]
    output_key: ArtifactKey[str]
    observed_mapping_api: bool | None = None

    def run(self, context: object, state: object) -> ModuleResult:
        self.observed_mapping_api = hasattr(state, "as_mapping")
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS",
            writes=(
                ArtifactWrite(
                    key=self.output_key,
                    value=state.require(self.required_key),  # type: ignore[union-attr]
                    producer_id=self.spec.module_id,
                ),
            ),
        )


def _catalog(*keys: ArtifactKey[object]) -> ArtifactCatalog:
    catalog = ArtifactCatalog()
    for key in keys:
        catalog.register(ArtifactDefinition(key=key, mode=ArtifactMode.EXCLUSIVE))
    return catalog


def _module(
    module_id: str,
    *,
    requires: tuple[ArtifactKey[object], ...] = (),
    provides: tuple[ArtifactKey[object], ...] = (),
    writes: tuple[ArtifactWrite[object], ...] = (),
    result_module_id: str | None = None,
) -> TypedModule:
    return TypedModule(
        spec=ModuleSpec(
            module_id=module_id,
            module_version="1.0.0",
            requires=frozenset(requires),
            provides=frozenset(provides),
        ),
        result=ModuleResult(
            module_id=result_module_id or module_id,
            status="PASS",
            writes=writes,
        ),
    )


def test_execute_exposes_initial_snapshot_through_typed_state_and_uses_only_writes():
    source = ArtifactKey("example.bootstrap", "1.0", str)
    retained = ArtifactKey("example.retained", "1.0", str)
    output = ArtifactKey("example.output", "1.0", str)
    catalog = _catalog(source, retained, output)
    initial_store = ArtifactStore(catalog)
    initial_store.write(ArtifactWrite(key=source, value="input", producer_id="bootstrap"))
    initial_store.write(ArtifactWrite(key=retained, value="keep", producer_id="bootstrap"))
    module = ReadingTypedModule(
        spec=ModuleSpec(
            module_id="consumer",
            module_version="1.0.0",
            requires=frozenset((source,)),
            provides=frozenset((output,)),
        ),
        required_key=source,
        output_key=output,
    )
    plan = ModulePlanCompiler(catalog).compile(
        (module,), initial_snapshot=initial_store.freeze()
    )

    execution = ResearchEngine().execute(plan, object(), catalog)

    assert execution.snapshot.require(source) == "input"
    assert execution.snapshot.require(retained) == "keep"
    assert execution.snapshot.require(output) == "input"
    assert module.observed_mapping_api is False
    assert tuple(result.module_id for result in execution.module_results) == ("consumer",)
    with pytest.raises(AttributeError):
        execution.module_results = ()  # type: ignore[misc]


def test_execute_rejects_an_initial_snapshot_that_differs_from_the_compiled_plan():
    source = ArtifactKey("example.bootstrap", "1.0", str)
    catalog = _catalog(source)
    compiled_store = ArtifactStore(catalog)
    compiled_store.write(
        ArtifactWrite(key=source, value="compiled", producer_id="bootstrap")
    )
    replacement_store = ArtifactStore(catalog)
    replacement_store.write(
        ArtifactWrite(key=source, value="replacement", producer_id="bootstrap")
    )
    plan = ModulePlanCompiler(catalog).compile(
        (), initial_snapshot=compiled_store.freeze()
    )

    with pytest.raises(PipelineDefinitionError, match="initial snapshot"):
        ResearchEngine().execute(
            plan,
            object(),
            catalog,
            initial_snapshot=replacement_store.freeze(),
        )


def test_execute_returns_module_results_in_compiled_plan_order():
    source = ArtifactKey("example.source", "1.0", str)
    output = ArtifactKey("example.output", "1.0", str)
    catalog = _catalog(source, output)
    provider = _module(
        "zeta",
        provides=(source,),
        writes=(ArtifactWrite(key=source, value="available", producer_id="zeta"),),
    )
    consumer = _module(
        "alpha",
        requires=(source,),
        provides=(output,),
        writes=(ArtifactWrite(key=output, value="done", producer_id="alpha"),),
    )
    plan = ModulePlanCompiler(catalog).compile((consumer, provider))

    execution = ResearchEngine().execute(plan, object(), catalog)

    assert tuple(result.module_id for result in execution.module_results) == ("zeta", "alpha")


@pytest.mark.parametrize(
    ("module", "match"),
    [
        (
            lambda key: _module(
                "provider",
                provides=(key,),
                writes=(ArtifactWrite(key=key, value="value", producer_id="provider"),),
                result_module_id="other",
            ),
            "identity mismatch",
        ),
        (
            lambda key: _module(
                "provider",
                provides=(),
                writes=(ArtifactWrite(key=key, value="value", producer_id="provider"),),
            ),
            "undeclared artifact write",
        ),
        (
            lambda key: _module(
                "provider",
                provides=(key,),
                writes=(ArtifactWrite(key=key, value="value", producer_id="other"),),
            ),
            "producer ID mismatch",
        ),
        (
            lambda key: _module("provider", provides=(key,)),
            "missing declared artifact writes",
        ),
        (
            lambda key: _module(
                "provider",
                provides=(key,),
                writes=(
                    ArtifactWrite(key=key, value="first", producer_id="provider"),
                    ArtifactWrite(key=key, value="second", producer_id="provider"),
                ),
            ),
            "duplicate artifact writes",
        ),
    ],
)
def test_execute_rejects_invalid_typed_module_results(module, match):
    key = ArtifactKey("example.output", "1.0", str)
    catalog = _catalog(key)
    plan = ModulePlanCompiler(catalog).compile((module(key),))

    with pytest.raises(PipelineDefinitionError, match=match) as captured:
        ResearchEngine().execute(plan, object(), catalog)

    assert captured.value.context == {"module_id": "provider"}


def test_execute_rechecks_runtime_value_type_before_storing_write():
    key = ArtifactKey("example.output", "1.0", int)
    catalog = _catalog(key)
    write = ArtifactWrite(key=key, value=1, producer_id="provider")
    object.__setattr__(write, "value", "wrong")
    module = _module("provider", provides=(key,), writes=(write,))
    plan = ModulePlanCompiler(catalog).compile((module,))

    with pytest.raises(PipelineDefinitionError, match="runtime value type mismatch"):
        ResearchEngine().execute(plan, object(), catalog)


def test_execute_preserves_module_failure_cause_and_run_context():
    class FailingModule:
        spec = ModuleSpec(module_id="broken", module_version="1.0.0")

        @staticmethod
        def run(context, state):
            raise RuntimeError("calculation exploded")

    catalog = ArtifactCatalog()
    plan = ModulePlanCompiler(catalog).compile((FailingModule(),))

    with pytest.raises(ModuleExecutionError) as captured:
        ResearchEngine().execute(
            plan,
            SimpleNamespace(run_id="run:broken"),
            catalog,
        )

    assert isinstance(captured.value.__cause__, RuntimeError)
    assert captured.value.context == {
        "run_id": "run:broken",
        "module_id": "broken",
    }


def test_core_runtime_has_one_typed_state_and_execution_api():
    key = ArtifactKey("example.output", "1.0", str)
    catalog = _catalog(key)
    module = _module(
        "provider",
        provides=(key,),
        writes=(ArtifactWrite(key=key, value="value", producer_id="provider"),),
    )
    plan = ModulePlanCompiler(catalog).compile((module,))

    execution = ResearchEngine().execute(plan, object(), catalog)
    result = execution.module_results[0]

    assert result.model_fields_set == {"module_id", "status", "writes"}
    assert result.diagnostics == ()
    assert not hasattr(result, "artifacts")
    assert not hasattr(result, "evidence_ids")
    assert not hasattr(ResearchEngine, "run")
    assert not hasattr(ResearchEngine, "_ordered_modules")
