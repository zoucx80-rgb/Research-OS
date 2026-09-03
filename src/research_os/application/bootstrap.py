"""Typed Bootstrap plan compilation for Core API 2.0 research runs."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

from research_os.application.command import ResearchRunCommand
from research_os.contracts.artifacts import ArtifactCatalog, ArtifactWrite
from research_os.contracts.evidence import EvidenceSet
from research_os.contracts.errors import RepositoryPreflightError
from research_os.router.classifier import BusinessModelRouter
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import (
    BUSINESS_MODEL_PROFILE,
    REPOSITORY_PREFLIGHT,
    build_core_artifact_catalog,
)
from research_os.runtime.financial_snapshot import (
    EVIDENCE_PIT,
    FINANCIAL_FACT_SNAPSHOT,
    FinancialFactSnapshotModule,
)
from research_os.runtime.module_plan import ModulePlan, ModulePlanCompiler
from research_os.runtime.modules import ModuleResult, ModuleSpec, ModuleStatus
from research_os.runtime.state import ResearchStateView
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


OFFICIAL_REPOSITORY_HOST = "github.com"
OFFICIAL_REPOSITORY = "zoucx80-rgb/Research-OS"
OFFICIAL_REPOSITORY_ID = 1350382205
OFFICIAL_BRANCH = "main"


@dataclass(frozen=True, slots=True)
class RepositoryAttestation:
    repository_host: str
    repository_full_name: str
    repository_id: int
    branch: str
    head_sha: str


class RepositoryAttestor(Protocol):
    def attest(self) -> RepositoryAttestation: ...


CommandRunner = Callable[[tuple[str, ...]], str]


def _run_command(command: tuple[str, ...]) -> str:
    return subprocess.check_output(command, text=True, timeout=5).strip()


def _github_coordinates(remote: str) -> tuple[str, str]:
    scp_match = re.fullmatch(r"git@([^:]+):(.+)", remote)
    if scp_match is not None:
        host, path = scp_match.groups()
    else:
        parsed = urlsplit(remote)
        host = parsed.hostname or ""
        path = parsed.path.lstrip("/")
    repository = path.removesuffix(".git")
    if host.lower() != OFFICIAL_REPOSITORY_HOST or repository != OFFICIAL_REPOSITORY:
        raise RepositoryPreflightError(
            "origin is not the exact official GitHub remote",
            context={"repository_remote": remote},
        )
    return host.lower(), repository


class GitRepositoryAttestor:
    """Attest local Git identity plus the CI-provided immutable GitHub repo ID."""

    def __init__(
        self,
        *,
        repository_root: Path | None = None,
        environment: Mapping[str, str] | None = None,
        command_runner: CommandRunner = _run_command,
    ) -> None:
        self._repository_root = repository_root or Path(__file__).resolve().parents[3]
        self._environment = dict(os.environ if environment is None else environment)
        self._command_runner = command_runner

    def _git(self, *arguments: str) -> str:
        try:
            return self._command_runner(
                ("git", "-C", str(self._repository_root), *arguments)
            ).strip()
        except (OSError, subprocess.SubprocessError) as exc:
            raise RepositoryPreflightError(
                "unable to attest local Git repository",
                context={"repository_root": str(self._repository_root)},
            ) from exc

    def attest(self) -> RepositoryAttestation:
        remote = self._git("remote", "get-url", "origin")
        host, repository = _github_coordinates(remote)
        attested_id = self._environment.get("GITHUB_REPOSITORY_ID")
        if attested_id is None:
            raise RepositoryPreflightError(
                "GitHub repository id attestation is required",
                context={"repository_full_name": repository},
            )
        try:
            repository_id = int(attested_id)
        except ValueError as exc:
            raise RepositoryPreflightError(
                "GitHub repository id must be a numeric repository id",
                context={"repository_id": attested_id},
            ) from exc
        environment_repository = self._environment.get("GITHUB_REPOSITORY")
        if environment_repository is not None and environment_repository != repository:
            raise RepositoryPreflightError(
                "GitHub repository attestation does not match origin",
                context={"repository_full_name": environment_repository},
            )
        server_url = self._environment.get("GITHUB_SERVER_URL")
        if server_url is not None and urlsplit(server_url).hostname != host:
            raise RepositoryPreflightError(
                "GitHub server attestation does not match origin",
                context={"repository_host": server_url},
            )
        return RepositoryAttestation(
            repository_host=host,
            repository_full_name=repository,
            repository_id=repository_id,
            branch=self._git("branch", "--show-current"),
            head_sha=self._git("rev-parse", "HEAD"),
        )


def validate_repository_attestation(
    context: ResearchContext,
    attestation: RepositoryAttestation,
) -> None:
    baseline = context.baseline
    checks = (
        (
            "repository host",
            attestation.repository_host == OFFICIAL_REPOSITORY_HOST,
        ),
        (
            "repository full name",
            baseline.repository_full_name == OFFICIAL_REPOSITORY
            and attestation.repository_full_name == OFFICIAL_REPOSITORY,
        ),
        (
            "repository id",
            baseline.repository_id == OFFICIAL_REPOSITORY_ID
            and attestation.repository_id == OFFICIAL_REPOSITORY_ID,
        ),
        (
            "repository branch",
            baseline.branch == OFFICIAL_BRANCH
            and attestation.branch in {"", OFFICIAL_BRANCH},
        ),
        (
            "repository HEAD",
            baseline.commit_sha == attestation.head_sha
            and bool(re.fullmatch(r"[0-9a-f]{40}", baseline.commit_sha)),
        ),
        (
            "Research OS version",
            baseline.research_os_version == RESEARCH_OS_VERSION,
        ),
        ("Core API version", baseline.core_api_version == CORE_API_VERSION),
    )
    for label, valid in checks:
        if not valid:
            raise RepositoryPreflightError(
                f"{label} validation failed",
                context={"run_id": context.run_id, "check": label},
            )


class BootstrapPreflightModule:
    """Project the already frozen repository baseline into a typed artifact."""

    spec = ModuleSpec(
        module_id="core:repository-preflight",
        module_version="2.0.0",
        provides=frozenset((REPOSITORY_PREFLIGHT,)),
    )

    def __init__(self, attestation: RepositoryAttestation) -> None:
        self._attestation = attestation

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        validate_repository_attestation(context, self._attestation)
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS",
            writes=(
                ArtifactWrite(
                    key=REPOSITORY_PREFLIGHT,
                    value=context.baseline,
                    producer_id=self.spec.module_id,
                ),
            ),
        )


class BootstrapPitModule:
    """Project the command's immutable, cutoff-bound evidence into Phase A."""

    spec = ModuleSpec(
        module_id="core:pit-lineage",
        module_version="2.0.0",
        requires=frozenset((REPOSITORY_PREFLIGHT,)),
        provides=frozenset((EVIDENCE_PIT,)),
    )

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        references = context.evidence.refs()
        evidence = tuple(
            item
            for reference in references
            if (item := context.evidence.get(reference)) is not None
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS" if evidence else "INSUFFICIENT_EVIDENCE",
            diagnostics=() if evidence else ("no evidence available at decision_ts",),
            writes=(
                ArtifactWrite(
                    key=EVIDENCE_PIT,
                    value=EvidenceSet(items=evidence, evidence_refs=references),
                    producer_id=self.spec.module_id,
                    evidence_refs=references,
                ),
            ),
        )


class BootstrapBusinessModelModule:
    """Classify the company using only the Phase A PIT artifact."""

    spec = ModuleSpec(
        module_id="core:business-model",
        module_version="2.0.0",
        requires=frozenset((EVIDENCE_PIT, FINANCIAL_FACT_SNAPSHOT)),
        provides=frozenset((BUSINESS_MODEL_PROFILE,)),
    )

    def __init__(self, router: BusinessModelRouter | None = None) -> None:
        self._router = router or BusinessModelRouter()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        evidence = state.require(EVIDENCE_PIT)
        profile = self._router.classify(
            context.company.company_id,
            list(evidence.items),
        )
        status: ModuleStatus = (
            "PASS"
            if profile.classification_status == "CLASSIFIED"
            else "INSUFFICIENT_EVIDENCE"
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            diagnostics=(
                ()
                if status == "PASS"
                else (profile.classification_reason or "business model unresolved",)
            ),
            writes=(
                ArtifactWrite(
                    key=BUSINESS_MODEL_PROFILE,
                    value=profile,
                    producer_id=self.spec.module_id,
                    evidence_refs=profile.evidence_refs,
                ),
            ),
        )


class BootstrapPlanCompiler:
    """Compile the fixed four-module Bootstrap phase."""

    def __init__(self, catalog: ArtifactCatalog | None = None) -> None:
        self.catalog = catalog or build_core_artifact_catalog()

    def compile(
        self,
        command: ResearchRunCommand,
        *,
        attestation: RepositoryAttestation,
    ) -> ModulePlan:
        modules = (
            BootstrapPreflightModule(attestation),
            BootstrapPitModule(),
            FinancialFactSnapshotModule(),
            BootstrapBusinessModelModule(),
        )
        return ModulePlanCompiler(self.catalog).compile(modules)
