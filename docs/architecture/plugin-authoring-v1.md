# Research OS Plugin Authoring Contract v1

Research OS v1.4.0 exposes a run-scoped plugin system behind `ResearchRuntimeFactory`. This document defines the supported authoring contract for Core API `1.0`.

## 1. Design boundary

Plugins extend research strategy; they do not own repository identity, PIT filtering, evidence lineage, completion policy, snapshot freezing, or the core execution engine. `ResearchEngine` remains generic and must not contain company, industry, or plugin identifiers.

A normal research run composes a fresh `PluginRegistry` for that run. Plugins must not rely on import-time global registry mutation or cross-run mutable registry state.

## 2. Plugin types

`PluginManifest.plugin_type` supports two orthogonal categories:

- `industry` — supplies strategy/capabilities for one or more routed business models and exposes `applicability(context)`, `modules()`, and `report_contributions()`.
- `methodology` — supplies cross-industry methodology and exposes `supports(context, state)` and `modules()`.

Industry and methodology plugins may be selected together when their capability contracts are compatible.

## 3. Manifest contract

Every plugin must expose a frozen `PluginManifest` containing:

- `plugin_id`
- `plugin_type`
- `plugin_version` using `MAJOR.MINOR.PATCH`
- `api_version`
- `min_research_os_version`
- optional `max_research_os_version`
- `provides`
- `requires`
- optional `supported_business_models`
- `priority`
- `maturity`, one of `experimental` or `stable`

For Core API v1, `api_version` must be `1.0`. `PluginRegistry` rejects duplicate IDs, invalid plugin shapes, incompatible API versions, invalid semantic versions, and Research OS versions outside the manifest range.

## 4. Capability contract

`provides` and `requires` are capability IDs, not implicit ordering hints. Module execution order is derived from capability dependencies. A plugin must declare every artifact/capability it provides and must not emit undeclared artifacts.

Industry auto-resolution currently considers industry plugins whose requirements are satisfiable from the base planning capability `business_model.profile`. Methodology selection occurs after selected industry capabilities are added to the planning state, so methodology plugins may depend on those capabilities.

## 5. Maturity and selection

`stable` plugins are eligible for normal automatic resolution. `experimental` plugins are excluded unless `ResearchOptions.allow_experimental_plugins` is enabled.

An explicit industry override still must be registered, support the routed primary business model, and satisfy the maturity rule. An experimental override therefore requires explicit experimental opt-in.

Automatic industry selection ranks eligible applicable candidates by applicability score, then manifest priority, then plugin ID for deterministic tie-breaking.

## 6. Registration and runtime composition

The supported extension point is a `PluginProvider` with:

```python
class MyProvider:
    def plugins(self):
        return [MyPlugin()]
```

Compose a runtime with:

```python
runtime = ResearchRuntimeFactory.with_providers(MyProvider())
result = runtime.run_context(context, inputs)
```

`ResearchRuntimeFactory.default()` uses the built-in provider. `with_providers(...)` is the explicit composition hook for external providers. Each run builds a fresh registry and fresh module composition from those providers.

Future entry-point catalogs, private plugin catalogs, or other discovery mechanisms should adapt into the same `PluginProvider` boundary rather than modifying `ResearchEngine`. They are extension directions, not bundled discovery mechanisms in v1.4.0.

## 7. Coverage gaps are first-class

If no compatible industry strategy exists for a routed business model, `StrategyResolver` returns a `CoverageGap` instead of pretending generic infrastructure is specialized coverage. Unsatisfied explicit methodology requests likewise produce methodology coverage gaps.

Coverage gaps must remain visible in `StrategyResolution` and downstream completion/reporting. A missing required research capability must never be silently converted into PASS or COMPLETE.

## 8. Failure and isolation rules

A plugin/module exception is surfaced with module identity by the core engine. Plugin failures must remain auditable and must not be translated into fabricated research evidence or hidden fallback conclusions.

Plugins must not:

- mutate this repository or any other repository as part of research execution;
- change global Git, shell, environment, editor, or system configuration;
- persist credentials or secrets;
- mutate a process-global plugin registry at import time;
- bypass PIT or evidence-lineage contracts;
- declare `FINAL_STATUS` or redefine `ResearchCompletionGate` policy;
- embed company/ticker-specific production branches as a substitute for a generic business-model contract.

## 9. Testing contract

New plugins should be validated with anonymous synthetic fixtures and must cover at least:

1. manifest/API/version compatibility;
2. applicability or methodology-support behavior;
3. declared capability dependencies and outputs;
4. automatic or explicit resolution behavior;
5. explicit coverage-gap behavior when unsupported;
6. failure isolation;
7. deterministic execution/fingerprints where applicable;
8. no changes required in `ResearchEngine` for the new plugin.

Research OS v1.4.0 release gates include plugin manifest, compatibility, resolution, coverage-gap, failure-isolation, extensibility, runtime-result, and snapshot-fingerprint checks.

## 10. Versioning

Plugin versions and Research OS compatibility ranges use standard semantic versioning. Research OS v1.4.0 keeps `CORE_API_VERSION = "1.0"`; compatible plugin additions do not require changing the core API version. A future incompatible plugin contract requires an explicit Core API version change rather than silent behavioral drift.
