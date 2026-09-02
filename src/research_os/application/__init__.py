"""Core API 2.0 application boundary."""

from research_os.contracts.errors import RepositoryPreflightError

from .bootstrap import (
    GitRepositoryAttestor,
    RepositoryAttestation,
    RepositoryAttestor,
)
from .command import (
    ExpectationResearchInput,
    ExternalVersionInputs,
    FinancialResearchInput,
    ForecastResearchInput,
    MonitoringResearchInput,
    PeerResearchInput,
    ResearchReadinessInput,
    ResearchRunCommand,
    ResearchRunOptions,
    ThesisResearchInput,
    ValuationModelInput,
    ValuationResearchInput,
)
from .result import (
    ComponentFingerprint,
    ResearchRunResult,
    ResearchSnapshotDescriptor,
    RunVersionSet,
    VersionIdentity,
)
from .service import PluginProvider, ResearchApplication

__all__ = [
    "ExpectationResearchInput",
    "ExternalVersionInputs",
    "FinancialResearchInput",
    "ForecastResearchInput",
    "GitRepositoryAttestor",
    "MonitoringResearchInput",
    "PeerResearchInput",
    "PluginProvider",
    "ResearchReadinessInput",
    "ResearchApplication",
    "RepositoryAttestation",
    "RepositoryAttestor",
    "RepositoryPreflightError",
    "ResearchRunResult",
    "ResearchRunCommand",
    "ResearchRunOptions",
    "ResearchSnapshotDescriptor",
    "RunVersionSet",
    "ThesisResearchInput",
    "ValuationModelInput",
    "ValuationResearchInput",
    "VersionIdentity",
    "ComponentFingerprint",
]
