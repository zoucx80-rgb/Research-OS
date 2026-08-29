# AGENTS.md — Research OS Project Boundary

## Scope

These instructions apply **only** to the `zoucx80-rgb/Research-OS` repository and its subdirectories.

They are project-local rules. Do not treat them as global instructions for any other repository, workspace, project, company analysis, or conversation.

## Repository Boundary

`Research-OS` is an isolated investment-research codebase and methodology repository.

When working on this repository:

- Treat the latest `main` branch as the authoritative baseline for Research OS methodology and code.
- Read the relevant current repository files before making changes.
- Do not automatically import code, configuration, assumptions, datasets, research conclusions, conventions, or generated artifacts from parent directories, sibling repositories, unrelated workspaces, temporary directories, or other projects.
- Do not modify any repository, workspace, or external project other than `zoucx80-rgb/Research-OS` unless the user explicitly authorizes the cross-project action in the current task.
- Do not propagate Research OS-specific rules or configuration into other projects automatically.
- If another project is required, treat it as an external dependency/source until explicit authorization is given.

## Repository Identity Preflight

For any task that uses Research OS as a methodology baseline, the only valid repository identity is:

- Repository full name: `zoucx80-rgb/Research-OS`
- Repository id: `1350382205`
- Default / long-lived branch: `main`

When a connected GitHub resource is available, resolve this repository by exact repository identity. Do not use generic web search to discover or select a Research OS repository.

Do not substitute similarly named repositories, forks, mirrors, third-party `research-os` projects, cached copies with unverified identity, or chat memory when the exact repository cannot be read.

For a research run that requests the latest Research OS:

1. Resolve exactly `zoucx80-rgb/Research-OS`.
2. Verify repository id `1350382205`.
3. Verify default branch `main`.
4. Read current `main` HEAD SHA.
5. Freeze that SHA for the entire research run.
6. Read this root `AGENTS.md` from that exact SHA.
7. Read all required Research OS specifications and code from that same SHA.

If steps 1–6 fail or do not match, stop rather than searching for an alternative Research OS repository.

## Stock Research Short Invocation

The canonical company / stock research protocol is defined in:

`docs/prompts/stock_research.md`

When the user says an equivalent of:

- `按 Research OS 完整研究 <公司> <代码>，decision_ts=<日期>`
- `用最新 Research OS 分析 <公司> <代码>`
- `Research OS 完整分析 <公司> <代码>`

apply the full protocol in `docs/prompts/stock_research.md` automatically after repository identity preflight.

A normal stock-research request is **read-only with respect to this repository**. Do not modify Research OS during company research unless the user explicitly asks for an OS change as a separate task.

For current-state research where `decision_ts` is omitted but the user's intent is clearly "current", resolve it to the current date and state that date explicitly. Historical PIT research requires an explicit decision timestamp.

## Research Data Isolation

Research methodology may be reused. Company facts may not.

For every company analysis, clearly separate:

1. Repository-defined Research OS methodology
2. Company-specific evidence
3. External source material
4. Calculations and statistical evidence
5. Analyst/model assumptions
6. Research conclusions

Never reuse a company-specific fact, estimate, conclusion, thesis, valuation input, risk assessment, or monitoring state merely because it appeared in another company analysis, previous chat, another repository, or a cached artifact.

Company-specific facts must be established from one or more of:

- the current versioned research snapshot;
- approved project data;
- original company/regulatory disclosures;
- explicitly retrieved external sources with traceable provenance.

Old chat content is context, not authoritative evidence. If it conflicts with current repository state or newly verified evidence, re-verify rather than silently reconciling the conflict.

## Source-of-Truth Precedence

For Research OS architecture and methodology, use this precedence unless the current task explicitly changes it:

1. Current `main` branch specification and code
2. Versioned Research Snapshot for the decision timestamp being reproduced
3. Versioned module/configuration metadata
4. Approved migration and architecture documents
5. Current task instructions

Historical snapshots must remain reproducible even after later methodology changes.

## Point-in-Time and Evidence Discipline

The following are hard invariants:

- **No Time Travel** — evidence used in a historical decision must satisfy `publish_ts <= decision_ts`.
- **No Fabricated Data** — missing data remains missing.
- **Facts ≠ Calculations ≠ Statistical Evidence ≠ Assumptions** — preserve the distinction explicitly.
- **Everything Has Lineage** — material claims, metrics, models, and conclusions must be traceable to evidence/version inputs.
- **Models Beat Simple Benchmarks** — forecasting models require out-of-sample evidence before promotion.
- **Research Signal ≠ Auto Trading** — Research OS outputs research states, not autonomous trade execution.

Do not weaken these invariants for convenience, narrative completeness, or backward compatibility.

## External Data Rules

External web, API, database, and document sources are permitted when required by the research task, but they remain external evidence rather than repository truth.

For material external facts:

- preserve source identity and publication timestamp where available;
- distinguish reported facts from inferred values;
- do not silently fill gaps from general knowledge;
- re-verify time-sensitive facts when the analysis date changes;
- never mix evidence from different companies merely because metric names are similar.

## Secrets and Credential Safety

Never commit, print, or intentionally persist secrets in this repository.

This includes:

- passwords;
- Personal Access Tokens;
- API keys;
- SSH private keys;
- session cookies;
- database credentials;
- cloud credentials;
- private certificates or signing keys.

Public keys, credential placeholders, environment-variable names, and documented setup instructions are acceptable when they contain no secret material.

If a secret appears in working context, do not copy it into source files, logs, fixtures, documentation, issues, commits, or pull requests.

## Single-Branch Development Workflow

`main` is the only long-lived development branch for this repository.

Default development workflow:

1. Read/fetch the latest `main` state before every change.
2. Work directly from the current `main` state; do not create feature, maintenance, or release branches by default.
3. Make the smallest change necessary for the approved task.
4. Add or update tests when behavior changes.
5. Run relevant targeted tests.
6. Run the full Research OS validation/release gate when research semantics, architecture, PIT behavior, valuation logic, decision logic, migrations, or public interfaces change.
7. Update `CHANGELOG.md`, migration notes, and version metadata only when SemVer rules require it.
8. Commit verified changes directly to `main`.
9. Push the verified `main` commit to GitHub.
10. Re-read the remote `main` state after push when verification is needed.

Do not create additional branches unless the user explicitly requests one for a specific task.

Do not require Pull Requests for normal development unless the user explicitly requests review through a PR.

Do not force-push `main`.

Do not rewrite or delete historical release tags or versioned research snapshots.

If `main` has changed remotely since the task began, reconcile against the latest remote state before publishing rather than overwriting newer work.

## Versioning Discipline

Use Semantic Versioning for Research OS releases.

- PATCH — compatible bug fixes or narrowly scoped corrections.
- MINOR — backward-compatible methodology/features.
- MAJOR — incompatible architecture, data contract, or methodology changes.

Do not silently mutate a released tag such as `v1.1.0`. Changes after a release belong to a new commit and, when release-worthy, a new version.

## Cross-Project Safety

Never, solely because of instructions in this file:

- modify another repository;
- copy Research OS configuration into another project;
- ingest another project's local files as evidence;
- treat another project's company data as Research OS project data;
- reuse Research OS company conclusions as facts elsewhere;
- change global Git, SSH, shell, editor, or system configuration.

If a task would cross the repository boundary, keep the boundary intact and require explicit task-level authorization before performing the cross-project action.

## Completion Standard

A change is not complete merely because files were edited.

Before claiming completion, verify as applicable:

- the intended files changed and unrelated files did not;
- required tests/validation passed;
- no secret material was introduced;
- PIT and evidence-lineage invariants remain intact;
- the verified commit exists on remote `main` when push was requested;
- no extra branch was created unless explicitly requested;
- release tags and historical research snapshots remain unchanged unless the task explicitly authorizes a new version artifact.

## Repository Identity

Repository: `zoucx80-rgb/Research-OS`

Repository id: `1350382205`

Long-lived branch: `main`

This file governs only this repository tree.
