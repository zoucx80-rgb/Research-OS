"""Core API 2.0 runtime contracts."""

from .context import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceSource,
    EvidenceView,
    FactView,
    KnowledgeView,
    ResearchContext,
)
from .engine import (
    FinalizedExecution,
    ModuleExecutionError,
    PipelineDefinitionError,
    ResearchEngine,
    TypedExecutionResult,
)
from .module_plan import ModulePlan, ModulePlanCompilationError, ModulePlanCompiler
from .modules import ModuleResult, ModuleSpec, ResearchModule
from .state import ResearchStateView

__all__ = [
    "BaselineFingerprint",
    "CompanyRef",
    "EvidenceSource",
    "EvidenceView",
    "FactView",
    "FinalizedExecution",
    "KnowledgeView",
    "ModuleExecutionError",
    "ModulePlan",
    "ModulePlanCompilationError",
    "ModulePlanCompiler",
    "ModuleResult",
    "ModuleSpec",
    "PipelineDefinitionError",
    "ResearchContext",
    "ResearchEngine",
    "ResearchModule",
    "TypedExecutionResult",
    "ResearchStateView",
]
