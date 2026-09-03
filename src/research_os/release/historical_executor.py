from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .replays import ReplayProfile


class HistoricalReplayError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class HistoricalReplayResult:
    profile_id: str
    source_commit_sha: str
    product_version: str
    output_dir: Path
    compatibility_actions: tuple[str, ...] = ()


class HistoricalReplayExecutor:
    """Execute one historical release from its own detached worktree and venv."""

    _PLAYWRIGHT_CLEANUP_PROFILE = "playwright-cleanup-v1.5.08"
    _PLAYWRIGHT_CLEANUP_COMMIT = "f7863e0b0aeb657ac19b0a63761788d40118e6bf"
    _PLAYWRIGHT_CLEANUP_PATH = Path("src/research_os/presentation/pdf_adapter.py")
    _PLAYWRIGHT_CLEANUP_BLOB = "4ba9ba1fefacb9776f46ad6d442480e6221594bd"
    _PLAYWRIGHT_REDUNDANT_CLEANUP = (
        "        finally:\n"
        "            if context is not None:\n"
        "                context.close()\n"
        "            if browser is not None and browser.is_connected():\n"
        "                browser.close()\n"
    )

    def __init__(self, repository_root: Path | None = None) -> None:
        self._repository_root = (repository_root or Path.cwd()).resolve()

    def execute(self, profile: ReplayProfile) -> HistoricalReplayResult:
        if not isinstance(profile, ReplayProfile):
            raise TypeError("HistoricalReplayExecutor.execute requires ReplayProfile")
        if not profile.frozen:
            raise HistoricalReplayError("historical replay profile must be frozen")
        output_dir = (self._repository_root / profile.output_dir).resolve()
        with tempfile.TemporaryDirectory(prefix="research-os-replay-") as temporary:
            temporary_root = Path(temporary)
            worktree = temporary_root / "worktree"
            venv = temporary_root / "venv"
            staging_output = temporary_root / "output"
            staging_output.mkdir(parents=True)
            self._git("cat-file", "-e", f"{profile.source_commit_sha}^{{commit}}")
            self._git(
                "worktree",
                "add",
                "--detach",
                "--force",
                str(worktree),
                profile.source_commit_sha,
            )
            try:
                actual_sha = self._run_text(
                    ["git", "rev-parse", "HEAD"], cwd=worktree
                )
                if actual_sha != profile.source_commit_sha:
                    raise HistoricalReplayError("historical worktree HEAD mismatch")
                metadata = self._metadata(worktree)
                product_version = str(metadata.get("research_os_version", ""))
                core_api_version = str(metadata.get("core_api_version", ""))
                if product_version != profile.expected_product_version:
                    raise HistoricalReplayError("historical product version mismatch")
                if core_api_version != profile.expected_core_api_version:
                    raise HistoricalReplayError("historical Core API version mismatch")
                runner = worktree / profile.runner_script
                fixture_dir = worktree / profile.fixture_dir
                if not runner.is_file() or not fixture_dir.is_dir():
                    raise HistoricalReplayError("historical replay source is incomplete")

                compatibility_actions = self._apply_compatibility_actions(
                    profile,
                    worktree=worktree,
                )
                self._run([sys.executable, "-m", "venv", str(venv)], cwd=worktree)
                python = self._venv_python(venv)
                self._run(
                    [
                        python,
                        "-m",
                        "pip",
                        "install",
                        "-q",
                        "-e",
                        f"{worktree}[pdf]",
                    ],
                    cwd=worktree,
                )
                environment = self._isolated_environment(
                    python=python,
                    venv=venv,
                    source_commit_sha=profile.source_commit_sha,
                )
                self._verify_import_identity(
                    profile,
                    worktree=worktree,
                    python=python,
                    environment=environment,
                )
                self._run(
                    [
                        python,
                        str(runner),
                        "--input-dir",
                        str(fixture_dir),
                        "--output-dir",
                        str(staging_output),
                        "--repository-root",
                        str(worktree),
                        "--commit-sha",
                        profile.source_commit_sha,
                    ],
                    cwd=worktree,
                    environment=environment,
                )
                if not any(staging_output.iterdir()):
                    raise HistoricalReplayError("historical replay produced no artifacts")
                self._publish_staged_output(staging_output, output_dir)
                self._write_replay_metadata(
                    output_dir,
                    profile=profile,
                    product_version=product_version,
                    compatibility_actions=compatibility_actions,
                )
                return HistoricalReplayResult(
                    profile_id=profile.profile_id,
                    source_commit_sha=profile.source_commit_sha,
                    product_version=product_version,
                    output_dir=output_dir,
                    compatibility_actions=compatibility_actions,
                )
            finally:
                self._git("worktree", "remove", "--force", str(worktree), check=False)
                self._git("worktree", "prune", check=False)

    def _apply_compatibility_actions(
        self,
        profile: ReplayProfile,
        *,
        worktree: Path,
    ) -> tuple[str, ...]:
        if profile.compatibility_profile is None:
            return ()
        if profile.compatibility_profile != self._PLAYWRIGHT_CLEANUP_PROFILE:
            raise HistoricalReplayError(
                f"unknown historical compatibility profile: {profile.compatibility_profile}"
            )
        adapter_path = worktree / self._PLAYWRIGHT_CLEANUP_PATH
        if not adapter_path.is_file():
            raise HistoricalReplayError("historical compatibility source is missing")
        source_blob_sha = self._run_text(
            ["git", "hash-object", str(self._PLAYWRIGHT_CLEANUP_PATH)],
            cwd=worktree,
        )
        action = self._resolve_compatibility_action(
            profile,
            source_blob_sha=source_blob_sha,
        )
        source = adapter_path.read_text(encoding="utf-8")
        if source.count(self._PLAYWRIGHT_REDUNDANT_CLEANUP) != 1:
            raise HistoricalReplayError(
                "historical compatibility cleanup shape mismatch"
            )
        adapter_path.write_text(
            source.replace(self._PLAYWRIGHT_REDUNDANT_CLEANUP, "", 1),
            encoding="utf-8",
        )
        changed = self._run_text(
            ["git", "status", "--porcelain", "--", str(self._PLAYWRIGHT_CLEANUP_PATH)],
            cwd=worktree,
        )
        # _run_text() strips leading whitespace, so a worktree-only porcelain
        # status of " M path" is observed here as "M path".
        expected_change = f"M {self._PLAYWRIGHT_CLEANUP_PATH.as_posix()}"
        if changed != expected_change:
            raise HistoricalReplayError(
                "historical compatibility modified an unexpected source surface"
            )
        return (action,)

    def _resolve_compatibility_action(
        self,
        profile: ReplayProfile,
        *,
        source_blob_sha: str,
    ) -> str:
        if profile.compatibility_profile != self._PLAYWRIGHT_CLEANUP_PROFILE:
            raise HistoricalReplayError("historical compatibility profile mismatch")
        if profile.source_commit_sha != self._PLAYWRIGHT_CLEANUP_COMMIT:
            raise HistoricalReplayError("historical compatibility commit mismatch")
        if source_blob_sha != self._PLAYWRIGHT_CLEANUP_BLOB:
            raise HistoricalReplayError(
                "historical compatibility source fingerprint mismatch"
            )
        return self._PLAYWRIGHT_CLEANUP_PROFILE

    @staticmethod
    def _publish_staged_output(staging_output: Path, output_dir: Path) -> None:
        if not staging_output.is_dir() or not any(staging_output.iterdir()):
            raise HistoricalReplayError("historical staged output is empty")
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        publish_dir = output_dir.with_name(f".{output_dir.name}.publishing")
        if publish_dir.exists():
            shutil.rmtree(publish_dir)
        shutil.copytree(staging_output, publish_dir)
        if output_dir.exists():
            shutil.rmtree(output_dir)
        publish_dir.replace(output_dir)

    @staticmethod
    def _write_replay_metadata(
        output_dir: Path,
        *,
        profile: ReplayProfile,
        product_version: str,
        compatibility_actions: tuple[str, ...],
    ) -> None:
        payload = {
            "profile_id": profile.profile_id,
            "source_commit_sha": profile.source_commit_sha,
            "product_version": product_version,
            "core_api_version": profile.expected_core_api_version,
            "compatibility_actions": list(compatibility_actions),
        }
        (output_dir / "_historical_replay.json").write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _verify_import_identity(
        self,
        profile: ReplayProfile,
        *,
        worktree: Path,
        python: str,
        environment: dict[str, str],
    ) -> None:
        probe = self._run_text(
            [
                python,
                "-c",
                (
                    "import json,research_os; "
                    "from research_os.version import RESEARCH_OS_VERSION,CORE_API_VERSION; "
                    "print(json.dumps({'module_file':research_os.__file__,"
                    "'product_version':RESEARCH_OS_VERSION,'core_api_version':CORE_API_VERSION}))"
                ),
            ],
            cwd=worktree,
            environment=environment,
        )
        try:
            identity = json.loads(probe)
            module_file = Path(str(identity["module_file"])).resolve()
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise HistoricalReplayError("historical import identity probe failed") from exc
        if not module_file.is_relative_to(worktree):
            raise HistoricalReplayError("historical import escaped the target worktree")
        if identity.get("product_version") != profile.expected_product_version:
            raise HistoricalReplayError("historical imported product version mismatch")
        if identity.get("core_api_version") != profile.expected_core_api_version:
            raise HistoricalReplayError("historical imported Core API version mismatch")

    @staticmethod
    def _isolated_environment(
        *, python: str, venv: Path, source_commit_sha: str
    ) -> dict[str, str]:
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        environment.update(
            {
                "GITHUB_SHA": source_commit_sha,
                "PYTHONNOUSERSITE": "1",
                "VIRTUAL_ENV": str(venv),
            }
        )
        environment["PATH"] = (
            str(Path(python).parent) + os.pathsep + environment.get("PATH", "")
        )
        return environment

    def _metadata(self, worktree: Path) -> dict[str, object]:
        path = worktree / "research_os_version.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HistoricalReplayError("historical release metadata is unreadable") from exc
        if not isinstance(value, dict):
            raise HistoricalReplayError("historical release metadata must be an object")
        return value

    @staticmethod
    def _venv_python(venv: Path) -> str:
        candidate = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not candidate.is_file():
            raise HistoricalReplayError("historical replay virtualenv is incomplete")
        return str(candidate)

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self._run(
            ["git", "-C", str(self._repository_root), *args],
            cwd=self._repository_root,
            check=check,
        )

    @staticmethod
    def _run_text(
        command: list[str],
        *,
        cwd: Path,
        environment: dict[str, str] | None = None,
    ) -> str:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    @staticmethod
    def _run(
        command: list[str],
        *,
        cwd: Path,
        environment: dict[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                cwd=cwd,
                env=environment,
                check=check,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise HistoricalReplayError(
                f"historical replay command failed: {' '.join(command[:3])}"
            ) from exc
