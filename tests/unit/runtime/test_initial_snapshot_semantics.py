from research_os.contracts.artifacts import (
    ArtifactCatalog,
    ArtifactDefinition,
    ArtifactKey,
    ArtifactMode,
    ArtifactStore,
    ArtifactWrite,
)
from research_os.runtime.engine import PipelineDefinitionError, ResearchEngine
from research_os.runtime.module_plan import ModulePlanCompiler


def _snapshot(value: str):
    key = ArtifactKey("example.bootstrap", "1.0", str)
    catalog = ArtifactCatalog()
    catalog.register(ArtifactDefinition(key=key, mode=ArtifactMode.EXCLUSIVE))
    store = ArtifactStore(catalog)
    store.write(ArtifactWrite(key=key, value=value, producer_id="bootstrap"))
    return key, catalog, store.freeze()


def test_engine_accepts_distinct_initial_snapshot_objects_with_same_semantics() -> None:
    key, catalog, compiled = _snapshot("same")
    replacement_store = ArtifactStore(catalog)
    replacement_store.write(ArtifactWrite(key=key, value="same", producer_id="bootstrap"))
    replacement = replacement_store.freeze()
    assert replacement is not compiled
    plan = ModulePlanCompiler(catalog).compile((), initial_snapshot=compiled)

    execution = ResearchEngine().execute(plan, object(), catalog, initial_snapshot=replacement)

    assert execution.snapshot.require(key) == "same"


def test_engine_rejects_distinct_initial_snapshot_semantics() -> None:
    key, catalog, compiled = _snapshot("compiled")
    replacement_store = ArtifactStore(catalog)
    replacement_store.write(ArtifactWrite(key=key, value="different", producer_id="bootstrap"))
    plan = ModulePlanCompiler(catalog).compile((), initial_snapshot=compiled)

    try:
        ResearchEngine().execute(
            plan, object(), catalog, initial_snapshot=replacement_store.freeze()
        )
    except PipelineDefinitionError as exc:
        assert "initial snapshot" in str(exc)
    else:
        raise AssertionError("different initial snapshot semantics must fail closed")
