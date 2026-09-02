from __future__ import annotations

import pytest

from research_os.contracts import (
    ArtifactProviderConflictError,
    ArtifactTypeMismatchError,
    CompletionEvaluationError,
    ContractError,
    CoreApiVersionMismatchError,
    PersistenceError,
    PluginContractError,
    PluginError,
    ResearchExecutionError,
    ResearchOSError,
    SnapshotSchemaError,
)
from research_os.plugins import PluginError as PublicPluginError
from research_os.plugins.discovery import PluginDiscoveryError, _load_plugin
from research_os.plugins.registry import (
    DuplicatePluginError,
    PluginVersionUnsupportedError,
)
from research_os.plugins.resolver import StrategyResolutionError
from research_os.runtime.engine import (
    ModuleExecutionError,
    PipelineDefinitionError,
)
from research_os.runtime.module_plan import ModulePlanCompilationError


def test_public_error_copies_and_freezes_diagnostic_context() -> None:
    source = {"run_id": "run:one", "module_id": "core:pit"}

    error = ResearchOSError("failed", context=source)
    source["run_id"] = "run:mutated"

    assert str(error) == "failed"
    assert error.code == "RESEARCH_OS_ERROR"
    assert error.context == {
        "run_id": "run:one",
        "module_id": "core:pit",
    }
    with pytest.raises(TypeError):
        error.context["run_id"] = "run:two"  # type: ignore[index]
    with pytest.raises(AttributeError):
        error.context = {}  # type: ignore[misc]
    with pytest.raises(AttributeError):
        error.code = "MUTATED"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("error_type", "code", "branch"),
    (
        (ArtifactTypeMismatchError, "ARTIFACT_TYPE_MISMATCH", ContractError),
        (
            ArtifactProviderConflictError,
            "ARTIFACT_PROVIDER_CONFLICT",
            ContractError,
        ),
        (PluginContractError, "PLUGIN_CONTRACT_ERROR", PluginError),
        (CoreApiVersionMismatchError, "CORE_API_VERSION_MISMATCH", ContractError),
        (SnapshotSchemaError, "SNAPSHOT_SCHEMA_ERROR", ContractError),
        (
            PluginVersionUnsupportedError,
            "PLUGIN_VERSION_UNSUPPORTED",
            PluginError,
        ),
        (DuplicatePluginError, "PLUGIN_DUPLICATE", PluginError),
        (PluginDiscoveryError, "PLUGIN_DISCOVERY_FAILED", PluginError),
        (StrategyResolutionError, "PLUGIN_STRATEGY_RESOLUTION_FAILED", PluginError),
        (ModulePlanCompilationError, "PLAN_COMPILATION_FAILED", ContractError),
        (
            PipelineDefinitionError,
            "PIPELINE_DEFINITION_ERROR",
            ResearchExecutionError,
        ),
        (
            ModuleExecutionError,
            "MODULE_EXECUTION_FAILED",
            ResearchExecutionError,
        ),
        (
            CompletionEvaluationError,
            "COMPLETION_EVALUATION_FAILED",
            ResearchExecutionError,
        ),
        (PersistenceError, "PERSISTENCE_ERROR", ResearchExecutionError),
    ),
)
def test_public_error_types_have_stable_codes_and_unified_branches(
    error_type: type[ResearchOSError],
    code: str,
    branch: type[ResearchOSError],
) -> None:
    error = error_type("failed")

    assert isinstance(error, ResearchOSError)
    assert isinstance(error, branch)
    assert error_type.code == code
    assert error.code == code
    assert error.context == {}


def test_plugin_error_branch_is_exported_by_the_plugin_package() -> None:
    assert PublicPluginError is PluginError


def test_plugin_discovery_preserves_cause_and_plugin_diagnostic_context() -> None:
    class Distribution:
        name = "broken-dist"

    class EntryPoint:
        name = "industry:broken"
        value = "broken.package:plugin"
        dist = Distribution()

        @staticmethod
        def load() -> object:
            raise RuntimeError("import exploded")

    with pytest.raises(PluginDiscoveryError) as captured:
        _load_plugin(EntryPoint())

    assert isinstance(captured.value.__cause__, RuntimeError)
    assert captured.value.context == {
        "distribution": "broken-dist",
        "entry_point": "industry:broken",
        "entry_point_value": "broken.package:plugin",
    }
