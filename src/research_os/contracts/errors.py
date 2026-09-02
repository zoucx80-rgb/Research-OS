from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType


class ResearchOSError(Exception):
    """Base for errors that cross a public Research OS boundary."""

    code = "RESEARCH_OS_ERROR"

    @property
    def context(self) -> Mapping[str, str]:
        return self._context

    def __setattr__(self, name: str, value: object) -> None:
        if name in {"code", "context"}:
            raise AttributeError(f"{name} is immutable")
        super().__setattr__(name, value)

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, str] | None = None,
    ) -> None:
        if not isinstance(message, str) or not message:
            raise TypeError("error message must be a non-empty string")
        copied_context = dict(context or {})
        if any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in copied_context.items()
        ):
            raise TypeError("error context must map strings to strings")
        super().__init__(message)
        self._context: Mapping[str, str] = MappingProxyType(copied_context)


class ContractError(ResearchOSError):
    """Base class for public contract violations."""

    code = "CONTRACT_ERROR"


class CoreApiVersionMismatchError(ContractError):
    code = "CORE_API_VERSION_MISMATCH"


class ArtifactContractError(ContractError):
    """Base class for typed artifact contract violations."""

    code = "ARTIFACT_CONTRACT_ERROR"


class ArtifactDefinitionError(ArtifactContractError):
    code = "ARTIFACT_DEFINITION_ERROR"


class ArtifactTypeMismatchError(ArtifactContractError):
    code = "ARTIFACT_TYPE_MISMATCH"


class ArtifactProviderConflictError(ArtifactContractError):
    code = "ARTIFACT_PROVIDER_CONFLICT"


class ArtifactNotFoundError(ArtifactContractError):
    code = "ARTIFACT_NOT_FOUND"


class PluginError(ContractError):
    """Base class for plugin loading, validation, and resolution errors."""

    code = "PLUGIN_ERROR"


class PluginContractError(PluginError):
    code = "PLUGIN_CONTRACT_ERROR"


class PluginVersionUnsupportedError(PluginContractError):
    code = "PLUGIN_VERSION_UNSUPPORTED"


class PlanCompilationError(ContractError):
    code = "PLAN_COMPILATION_FAILED"


class SnapshotSchemaError(ContractError):
    code = "SNAPSHOT_SCHEMA_ERROR"


class ResearchExecutionError(ResearchOSError):
    """Base class for failures during an otherwise valid research execution."""

    code = "RESEARCH_EXECUTION_ERROR"


class RepositoryPreflightError(ResearchExecutionError):
    code = "REPOSITORY_PREFLIGHT_FAILED"


class CompletionEvaluationError(ResearchExecutionError):
    code = "COMPLETION_EVALUATION_FAILED"


class PersistenceError(ResearchExecutionError):
    code = "PERSISTENCE_ERROR"
