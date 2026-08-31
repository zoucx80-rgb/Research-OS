# Release Governance Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace patch-version-specific release plumbing with a canonical release manifest, reusable verification packs, frozen replay profiles, and a stable CI verification entry point.

**Architecture:** `CURRENT_RELEASE` owns release identity and enabled capability packs. A reusable verification registry resolves those packs into checks, a replay registry resolves field acceptance profiles, and stable release scripts/CI consume those abstractions without knowing the current patch version. Historical replay implementations remain versioned only as frozen compatibility contracts.

**Tech Stack:** Python 3.12, dataclasses, setuptools dynamic version metadata, pytest, GitHub Actions, Playwright PDF integration.

**Spec:** `docs/superpowers/specs/2026-08-31-release-governance-architecture.md`

## Global Constraints

- Research OS target remains `1.5.11`; Core API remains `1.0`.
- No company/security identifier branches or acceptance-company facts in production code.
- Reporting/presentation/release infrastructure must not recompute research semantics.
- Historical v1.5.08-v1.5.10 replay must remain green and frozen.
- Future patch releases must not require a new version-specific release runtime module or CI block.
- Final `main` integration must contain exactly one v1.5.11 release commit on top of v1.5.10.

---

### Task 1: Governance Invariant Tests

**Files:**
- Create: `tests/regression/architecture/test_release_governance.py`

**Interfaces:**
- Consumes: current repository layout and release surfaces.
- Produces: invariant tests defining the new architecture before implementation.

- [ ] **Step 1: Write failing architecture tests**

Test that:

```python
from research_os.release.manifest import CURRENT_RELEASE
from research_os.release.verification import resolve_release_checks

assert research_os.__version__ == CURRENT_RELEASE.version
assert resolve_release_checks(CURRENT_RELEASE)
```

and assert `pyproject.toml` uses dynamic versioning, `research_os_version.json` equals `CURRENT_RELEASE.to_public_metadata()`, no `runtime_v*.py` release module exists, `release/gate.py` does not enumerate semantic check ids, CI invokes `scripts/verify_release_pipeline.py`, replay profiles are unique, and every resolved pytest path exists.

- [ ] **Step 2: Run the governance test and verify RED**

Run:

```bash
pytest -q tests/regression/architecture/test_release_governance.py
```

Expected: collection/import failures because manifest/verification/replay abstractions do not exist yet.

- [ ] **Step 3: Commit the RED contract**

```bash
git add tests/regression/architecture/test_release_governance.py
git commit -m "test: define release governance invariants"
```

### Task 2: Canonical Release Manifest and Dynamic Package Version

**Files:**
- Create: `src/research_os/release/manifest.py`
- Modify: `src/research_os/version.py`
- Modify: `pyproject.toml`
- Create: `scripts/sync_release_metadata.py`
- Modify: `research_os_version.json`
- Modify: `tests/unit/test_version_consistency_v1_2_1.py`

**Interfaces:**
- Produces: `ReleaseManifest`, `CURRENT_RELEASE`, `ReleaseManifest.to_public_metadata()`.
- `research_os.version.RESEARCH_OS_VERSION` and `CORE_API_VERSION` derive from `CURRENT_RELEASE`.

- [ ] **Step 1: Implement immutable release manifest**

Use a frozen dataclass with typed fields:

```python
@dataclass(frozen=True)
class ReleaseManifest:
    version: str
    core_api_version: str
    status: str
    module_versions: Mapping[str, str]
    verification_packs: tuple[str, ...]
    field_replay_profiles: tuple[str, ...]

    def to_public_metadata(self) -> dict[str, object]: ...
```

Set `CURRENT_RELEASE` to v1.5.11 and current component fingerprints.

- [ ] **Step 2: Make public version constants derive from manifest**

`src/research_os/version.py` becomes:

```python
from research_os.release.manifest import CURRENT_RELEASE

RESEARCH_OS_VERSION = CURRENT_RELEASE.version
CORE_API_VERSION = CURRENT_RELEASE.core_api_version
```

- [ ] **Step 3: Make setuptools version dynamic**

Replace `[project] version = "1.5.11"` with:

```toml
[project]
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "research_os.version.RESEARCH_OS_VERSION"}
```

- [ ] **Step 4: Add metadata generator**

`scripts/sync_release_metadata.py` serializes `CURRENT_RELEASE.to_public_metadata()` deterministically into `research_os_version.json`.

- [ ] **Step 5: Update version consistency tests**

Assert dynamic packaging configuration and manifest/JSON equality instead of comparing three independently maintained literals.

- [ ] **Step 6: Run focused tests**

```bash
pytest -q tests/unit/test_version_consistency_v1_2_1.py tests/regression/architecture/test_release_governance.py
```

Expected: remaining failures only for verification/replay/CI abstractions.

### Task 3: Verification Registry, Packs, and Generic Release Gate

**Files:**
- Create: `src/research_os/release/verification.py`
- Modify: `src/research_os/release/runtime.py`
- Modify: `src/research_os/release/gate.py`
- Delete: `src/research_os/release/runtime_v1_5_11.py`
- Modify: `scripts/release_gate_v1_1.py`
- Modify: `tests/regression/architecture/test_release_contract_v1_5_11.py`

**Interfaces:**
- Produces: `VerificationPack`, `CHECK_REGISTRY`, `VERIFICATION_PACKS`, `resolve_release_checks(manifest)`, `run_release_checks()`.

- [ ] **Step 1: Move v1.5.11 semantic checks into reusable pack**

Create stable check ids without making `gate.py` own them. Preserve existing historical/base registry and define:

```python
VERIFICATION_PACKS = {
    "stable-baseline": VerificationPack(...),
    "semantic-correctness": VerificationPack(...),
}
```

- [ ] **Step 2: Resolve checks from manifest**

Fail closed for unknown packs and duplicate check ids. Preserve deterministic order.

- [ ] **Step 3: Make runtime a compatibility facade**

`release.runtime.CHECKS` becomes the current resolved mapping and `run_release_checks()` delegates to it. No future version-specific runtime module is required.

- [ ] **Step 4: Derive release gate requirements**

`gate.REQUIRED` is `tuple(resolve_release_checks(CURRENT_RELEASE))`; no check list is duplicated.

- [ ] **Step 5: Make release script generic**

`scripts/release_gate_v1_1.py` imports `run_release_checks` from `research_os.release.runtime` only.

- [ ] **Step 6: Remove `runtime_v1_5_11.py` and update contracts**

Release-contract tests assert generic invariants and component fingerprints from `CURRENT_RELEASE`, not duplicated literal ownership.

- [ ] **Step 7: Run release governance/gate tests**

```bash
pytest -q tests/regression/architecture/test_release_governance.py tests/regression/architecture/test_release_contract_v1_5_11.py tests/unit/test_version_consistency_v1_2_1.py
```

Expected: only replay/CI pipeline assertions remain RED.

### Task 4: Frozen Replay Registry and Stable CI Pipeline

**Files:**
- Create: `src/research_os/release/replays.py`
- Create: `scripts/verify_release_pipeline.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/regression/architecture/test_release_governance.py`

**Interfaces:**
- Produces: `FieldReplayProfile`, `REPLAY_REGISTRY`, `resolve_replay_profiles(manifest)`, generic release pipeline CLI.

- [ ] **Step 1: Register replay profiles declaratively**

Profiles cover frozen v1.5.08, v1.5.09, v1.5.10 and current v1.5.11 with runner, fixture directory, output directory, and frozen flag.

- [ ] **Step 2: Implement generic replay orchestration**

The pipeline validates metadata, runs resolved release checks, executes replay profiles in manifest order, runs full pytest, and runs the generic release gate. Every stage prints a stable label and propagates non-zero exit status.

- [ ] **Step 3: Simplify CI**

Keep environment setup and Playwright/font installation. Replace per-version pytest/render blocks with one `python scripts/verify_release_pipeline.py` step and one upload of `build/field-acceptance-*`.

- [ ] **Step 4: Verify CI architecture**

Governance test asserts CI contains the stable pipeline command and no `render_field_acceptance_v1_5_XX.py` command literals.

- [ ] **Step 5: Run focused architecture tests**

```bash
pytest -q tests/regression/architecture/test_release_governance.py tests/regression/architecture/test_release_contract_v1_5_11.py
```

Expected: PASS.

### Task 5: Full Historical and v1.5.11 Verification

**Files:**
- Modify only if tests reveal a concrete defect.

**Interfaces:**
- Consumes: completed release-governance architecture.
- Produces: fresh evidence that historical replay, current semantic correctness, PDF field output, full test suite, and release gate all pass.

- [ ] **Step 1: Run the stable pipeline**

```bash
python scripts/verify_release_pipeline.py
```

Expected: metadata PASS, all release checks PASS, v1.5.08-v1.5.11 replay PASS, full pytest PASS, release gate READY.

- [ ] **Step 2: Inspect generated v1.5.11 acceptance manifest**

Confirm presentation and semantic correctness are PASS and generated Markdown/HTML/PDF exist.

- [ ] **Step 3: Run source-scope scan**

Verify no acceptance-company ids/names occur under `src/research_os` and no version-specific release runtime module exists.

### Task 6: Single-Commit v1.5.11 Main Integration

**Files:**
- No content changes after branch verification unless release evidence finds a defect.

**Interfaces:**
- Produces: one main release commit for v1.5.11.

- [ ] **Step 1: Freeze feature HEAD and tree SHA after GREEN CI**

Record exact branch HEAD and tree.

- [ ] **Step 2: Re-read main HEAD**

Require `main` to still be v1.5.10 `05a3ba99edc02ac93ee9fdf1130485da7e6fa8ab`; if it moved, re-evaluate before writing.

- [ ] **Step 3: Create squash release commit from final feature tree**

Create one commit with parent v1.5.10 main and message:

```text
release: semantic correctness and release governance v1.5.11
```

- [ ] **Step 4: Fast-forward `main` to the release commit**

No force update.

- [ ] **Step 5: Verify main topology**

Compare v1.5.10 main to new main and require:

```text
ahead_by = 1
behind_by = 0
total_commits = 1
```

- [ ] **Step 6: Verify fresh exact-main CI**

Require the workflow for the exact new main SHA to complete successfully before claiming completion.
