from __future__ import annotations

from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from research_os.contracts.artifacts import (
    ArtifactCatalog,
    ArtifactDefinition,
    ArtifactKey,
    ArtifactMode,
    ArtifactStore,
    ArtifactWrite,
)
from research_os.contracts.errors import ArtifactDefinitionError
from research_os.runtime.module_plan import ModulePlanCompilationError, ModulePlanCompiler
from research_os.runtime.modules import ModuleSpec


@dataclass
class TypedModule:
    spec: ModuleSpec


def _module(
    module_id: str,
    *,
    requires: tuple[ArtifactKey[object], ...] = (),
    provides: tuple[ArtifactKey[object], ...] = (),
) -> TypedModule:
    return TypedModule(
        ModuleSpec(
            module_id=module_id,
            module_version="1.0.0",
            requires=frozenset(requires),
            provides=frozenset(provides),
        )
    )


def _catalog(*definitions: ArtifactDefinition[object]) -> ArtifactCatalog:
    catalog = ArtifactCatalog()
    for definition in definitions:
        if definition.mode is ArtifactMode.COLLECTION:
            catalog.register(definition, reducer=lambda values: tuple(values))
        else:
            catalog.register(definition)
    return catalog


def test_compiler_topologically_sorts_typed_artifact_dependencies_deterministically():
    source = ArtifactKey("example.source", "1.0", str)
    derived = ArtifactKey("example.derived", "1.0", str)
    catalog = _catalog(
        ArtifactDefinition(key=source, mode=ArtifactMode.EXCLUSIVE),
        ArtifactDefinition(key=derived, mode=ArtifactMode.EXCLUSIVE),
    )
    modules = (
        _module("zeta"),
        _module("beta", requires=(source,), provides=(derived,)),
        _module("alpha", provides=(source,)),
    )

    forward = ModulePlanCompiler(catalog).compile(modules)
    reverse = ModulePlanCompiler(catalog).compile(tuple(reversed(modules)))

    assert forward.module_ids == ("alpha", "beta", "zeta")
    assert reverse.module_ids == forward.module_ids


def test_compiler_allows_initial_typed_artifact_to_satisfy_requirement():
    source = ArtifactKey("example.bootstrap", "1.0", str)
    derived = ArtifactKey("example.output", "1.0", str)
    catalog = _catalog(
        ArtifactDefinition(key=source, mode=ArtifactMode.EXCLUSIVE),
        ArtifactDefinition(key=derived, mode=ArtifactMode.EXCLUSIVE),
    )
    store = ArtifactStore(catalog)
    store.write(ArtifactWrite(key=source, value="available", producer_id="bootstrap"))

    plan = ModulePlanCompiler(catalog).compile(
        (_module("consumer", requires=(source,), provides=(derived,)),),
        initial_snapshot=store.freeze(),
    )

    assert plan.module_ids == ("consumer",)


def test_compiler_rejects_provider_for_artifact_already_in_initial_snapshot():
    source = ArtifactKey("example.bootstrap", "1.0", str)
    catalog = _catalog(ArtifactDefinition(key=source, mode=ArtifactMode.EXCLUSIVE))
    store = ArtifactStore(catalog)
    store.write(ArtifactWrite(key=source, value="available", producer_id="bootstrap"))

    with pytest.raises(ModulePlanCompilationError, match="initial snapshot.*example.bootstrap"):
        ModulePlanCompiler(catalog).compile(
            (_module("duplicate", provides=(source,)),),
            initial_snapshot=store.freeze(),
        )


def test_compiler_wraps_initial_snapshot_type_mismatch():
    registered = ArtifactKey("example.bootstrap", "1.0", str)
    incompatible = ArtifactKey("example.bootstrap", "1.0", int)
    catalog = _catalog(ArtifactDefinition(key=registered, mode=ArtifactMode.EXCLUSIVE))
    other_catalog = _catalog(ArtifactDefinition(key=incompatible, mode=ArtifactMode.EXCLUSIVE))
    store = ArtifactStore(other_catalog)
    store.write(ArtifactWrite(key=incompatible, value=1, producer_id="bootstrap"))

    with pytest.raises(ModulePlanCompilationError, match="initial snapshot.*example.bootstrap"):
        ModulePlanCompiler(catalog).compile(
            (_module("consumer", requires=(registered,)),),
            initial_snapshot=store.freeze(),
        )


def test_compiler_rejects_duplicate_module_ids():
    with pytest.raises(ModulePlanCompilationError, match="duplicate module_id: duplicate"):
        ModulePlanCompiler(ArtifactCatalog()).compile((_module("duplicate"), _module("duplicate")))


def test_compiler_rejects_multiple_providers_for_exclusive_artifact():
    key = ArtifactKey("example.exclusive", "1.0", str)
    catalog = _catalog(ArtifactDefinition(key=key, mode=ArtifactMode.EXCLUSIVE))

    with pytest.raises(ModulePlanCompilationError, match="exclusive.*example.exclusive"):
        ModulePlanCompiler(catalog).compile(
            (_module("first", provides=(key,)), _module("second", provides=(key,)))
        )


def test_compiler_rejects_collection_artifact_without_reducer():
    key = ArtifactKey("example.collection", "1.0", tuple)

    class BrokenCatalog:
        def definition(self, requested_key):
            assert requested_key == key
            return type("Definition", (), {"mode": ArtifactMode.COLLECTION})()

        def reducer(self, requested_key):
            assert requested_key == key
            raise ArtifactDefinitionError("collection artifact has no reducer implementation")

    with pytest.raises(ModulePlanCompilationError, match="collection.*reducer"):
        ModulePlanCompiler(BrokenCatalog()).compile((_module("provider", provides=(key,)),))


def test_compiler_rejects_missing_typed_dependency():
    missing = ArtifactKey("example.missing", "1.0", str)
    catalog = _catalog(ArtifactDefinition(key=missing, mode=ArtifactMode.EXCLUSIVE))

    with pytest.raises(ModulePlanCompilationError, match="consumer.*example.missing") as captured:
        ModulePlanCompiler(catalog).compile((_module("consumer", requires=(missing,)),))

    assert captured.value.context == {
        "module_id": "consumer",
        "artifact_id": "example.missing",
        "schema_version": "1.0",
    }
    assert captured.value.code == "PLAN_DEPENDENCY_MISSING"


def test_compiler_rejects_typed_dependency_cycles():
    first = ArtifactKey("example.first", "1.0", str)
    second = ArtifactKey("example.second", "1.0", str)
    catalog = _catalog(
        ArtifactDefinition(key=first, mode=ArtifactMode.EXCLUSIVE),
        ArtifactDefinition(key=second, mode=ArtifactMode.EXCLUSIVE),
    )

    with pytest.raises(ModulePlanCompilationError, match="cycle.*alpha.*beta") as captured:
        ModulePlanCompiler(catalog).compile(
            (
                _module("beta", requires=(first,), provides=(second,)),
                _module("alpha", requires=(second,), provides=(first,)),
            )
        )

    assert captured.value.context == {"module_ids": "alpha,beta"}
    assert captured.value.code == "PLAN_DEPENDENCY_CYCLE"


def test_module_spec_rejects_legacy_string_capabilities_and_has_only_typed_fields():
    with pytest.raises(ValidationError):
        ModuleSpec(
            module_id="typed",
            module_version="1.0.0",
            requires=frozenset({"legacy.capability"}),  # type: ignore[arg-type]
        )


def test_module_spec_exposes_only_typed_dependency_fields():
    source = ArtifactKey("example.source", "1.0", str)
    output = ArtifactKey("example.output", "1.0", str)
    spec = ModuleSpec(
        module_id="typed",
        module_version="1.0.0",
        requires=frozenset((source,)),
        provides=frozenset((output,)),
    )

    assert spec.requires == frozenset((source,))
    assert spec.provides == frozenset((output,))
    assert not hasattr(spec, "artifact_requires")
    assert not hasattr(spec, "artifact_provides")
