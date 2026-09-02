from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from research_os.application import (
    GitRepositoryAttestor,
    ResearchApplication,
    RepositoryAttestation,
    RepositoryAttestor,
    RepositoryPreflightError,
)
from research_os.plugins.protocols import ResearchPlugin
from research_os.contracts.errors import PluginContractError
from tests.integration.runtime.test_research_application import _command


class StaticAttestor:
    def __init__(self, attestation: RepositoryAttestation) -> None:
        self.attestation = attestation

    def attest(self) -> RepositoryAttestation:
        return self.attestation


def test_repository_attestor_is_a_public_injection_contract() -> None:
    attestor: RepositoryAttestor = StaticAttestor(_attestation())
    assert attestor.attest() == _attestation()


class RecordingPluginProvider:
    def __init__(self) -> None:
        self.called = False

    def plugins(self) -> tuple[ResearchPlugin, ...]:
        self.called = True
        return ()


class ExplodingPluginProvider:
    def plugins(self) -> tuple[ResearchPlugin, ...]:
        raise RuntimeError("provider exploded")


def _attestation(**updates: object) -> RepositoryAttestation:
    command = _command()
    values: dict[str, object] = {
        "repository_host": "github.com",
        "repository_full_name": "zoucx80-rgb/Research-OS",
        "repository_id": 1350382205,
        "branch": "main",
        "head_sha": command.context.baseline.commit_sha,
    }
    values.update(updates)
    return RepositoryAttestation(**values)  # type: ignore[arg-type]


def test_application_preflight_runs_before_any_plugin_provider_code() -> None:
    provider = RecordingPluginProvider()
    application = ResearchApplication.build(
        plugin_providers=(provider,),
        repository_attestor=StaticAttestor(_attestation(repository_id=1)),
    )

    with pytest.raises(RepositoryPreflightError, match="repository id"):
        application.run(_command())

    assert provider.called is False


def test_application_defers_builtin_plugin_provider_until_after_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class Builtins:
        def __init__(self) -> None:
            calls.append("constructed")

        def plugins(self) -> tuple[ResearchPlugin, ...]:
            calls.append("queried")
            return ()

    monkeypatch.setattr(
        "research_os.application.service.BuiltinPluginProvider",
        Builtins,
    )
    application = ResearchApplication.build(
        repository_attestor=StaticAttestor(_attestation(repository_id=1)),
    )

    with pytest.raises(RepositoryPreflightError):
        application.run(_command())

    assert calls == []


def test_application_wraps_plugin_provider_failures_with_run_context() -> None:
    application = ResearchApplication.build(
        plugin_providers=(ExplodingPluginProvider(),),
        repository_attestor=StaticAttestor(_attestation()),
    )

    with pytest.raises(PluginContractError) as captured:
        application.run(_command())

    assert isinstance(captured.value.__cause__, RuntimeError)
    assert captured.value.context["run_id"] == "run:application"
    assert captured.value.context["provider_type"] == "ExplodingPluginProvider"


def test_git_attestor_rejects_suffix_matched_evil_github_host() -> None:
    outputs = {
        "rev-parse": _attestation().head_sha,
        "branch": "main",
        "remote": "git@evilgithub.com:zoucx80-rgb/Research-OS.git",
    }

    def run(command: tuple[str, ...]) -> str:
        return next(value for key, value in outputs.items() if key in command)

    attestor = GitRepositoryAttestor(
        repository_root=Path("/repository"),
        environment={
            "GITHUB_REPOSITORY_ID": "1350382205",
            "GITHUB_REPOSITORY": "zoucx80-rgb/Research-OS",
            "GITHUB_SERVER_URL": "https://github.com",
        },
        command_runner=run,
    )

    with pytest.raises(RepositoryPreflightError, match="GitHub remote"):
        attestor.attest()


def test_git_attestor_fails_closed_without_repository_id_attestation() -> None:
    def run(command: tuple[str, ...]) -> str:
        if "rev-parse" in command:
            return _attestation().head_sha
        if "branch" in command:
            return "main"
        return "git@github.com:zoucx80-rgb/Research-OS.git"

    attestor = GitRepositoryAttestor(
        repository_root=Path("/repository"),
        environment={},
        command_runner=run,
    )

    with pytest.raises(RepositoryPreflightError, match="repository id attestation"):
        attestor.attest()


def test_git_attestor_accepts_exact_github_identity_and_attested_id() -> None:
    environment: Mapping[str, str] = {
        "GITHUB_REPOSITORY_ID": "1350382205",
        "GITHUB_REPOSITORY": "zoucx80-rgb/Research-OS",
        "GITHUB_SERVER_URL": "https://github.com",
    }

    def run(command: tuple[str, ...]) -> str:
        if "rev-parse" in command:
            return _attestation().head_sha
        if "branch" in command:
            return "main"
        return "https://github.com/zoucx80-rgb/Research-OS.git"

    attestor = GitRepositoryAttestor(
        repository_root=Path("/repository"),
        environment=environment,
        command_runner=run,
    )

    assert attestor.attest() == _attestation()
