# Research OS v1.5.12 Semantic Preservation & Valuation Reconciliation Design

## 1. Goal

Prevent canonical research meaning from being weakened, strengthened, or stripped of material qualifiers while it moves through:

```text
ResearchRunResult -> HumanReadableResearchView -> ResearchReportDocument -> Markdown
```

The release also adds a canonical valuation-reconciliation boundary. Presentation may format a reconciliation result but must not calculate intersections, cross-check bands, or disagreement.

## 2. Audit findings mapped to architectural defects

| Audit finding | Generic defect | Owning boundary | Required contract |
| --- | --- | --- | --- |
| Technical evidence rendered as a confirmed economic moat | Domain semantics collapse distinct barrier types and realization states | `semantics/claims` | Typed moat evidence and realization state; economic realization requires economic outcome evidence |
| Sensitivity output loses assumptions | Scenario result and assumptions are separate optional payloads | `completeness` | A rendered scenario result carries material assumptions, model boundary, applicability and caveats |
| KPI thresholds look like objective standards | Threshold provenance is too coarse and not mandatory in the body | `completeness` | Threshold type, source, rationale, comparison basis and applicability travel together |
| Observed recovery becomes “trough confirmed” | Claim strength and cycle state are implicit prose | `semantics/claims` | Typed claim strength plus `RECOVERY_OBSERVED`, `TROUGH_UNCONFIRMED`, `TROUGH_CONFIRMED` |
| DCF downgrade cites a software version | Analytical rationale accepts audit metadata | `valuation` | Model-fitness rationale is economic-only and rejects release/renderer/version provenance |
| Multiple valuation ranges are forced into a pretty range | No canonical cross-model reconciliation | `valuation/reconciliation` | Typed basis/role plus `INTERSECTION`, `CROSS_CHECK_BAND`, `MODEL_DISAGREEMENT`, `NOT_COMPARABLE` |
| View/Document/Markdown lose qualifiers | No machine-verifiable preservation contract | `semantics/preservation` | Stable semantic fingerprints across canonical, view and document projections |

## 3. Boundaries

- New semantic models live in a stable `research_os.semantics` bounded context; no `*_v1_5_12.py` runtime chain is introduced.
- Existing v1.5.11 thesis signal types and comparison-basis safety remain unchanged.
- The active runtime may add semantic artifacts through new reusable modules. Historical replay adapters remain pinned.
- `CORE_API_VERSION` remains `1.0`; all new input fields are additive.
- No company id, security code, issuer name, or steel/superalloy special case may appear in `src/research_os`.
- `decision_ts=2026-08-30` is fixed for the real-company field fixture. Evidence published after that timestamp is rejected.

## 4. Semantic contracts

### 4.1 Claim strength

`ClaimStrength` is ordered as:

```text
OBSERVED < SUGGESTIVE < SUPPORTED < STRONG < CONFIRMED
```

The policy is fail-closed:

- missing evidence -> at most `OBSERVED`;
- non-comparable evidence -> at most `SUGGESTIVE`;
- one good source without independent confirmation -> at most `SUPPORTED`;
- `CONFIRMED` requires comparable evidence, no material missingness and independent confirmation.

### 4.2 Sensitivity contract

A `SensitivityCase` that exposes a numerical result for the active release must carry:

- one or more material assumptions;
- `model_boundary`;
- `applicability`;
- optional caveats and lineage.

The active semantic-validation module rejects incomplete cases before presentation. Historical replay keeps its frozen adapter behavior.

### 4.3 Threshold contract

Threshold types are:

```text
company_guidance
accounting_or_regulatory
industry_benchmark
historical_company_benchmark
analyst_defined_monitoring
contractual
other
```

An analyst-defined threshold is always labeled as a research monitoring line in the investor-facing body.

### 4.4 Valuation reconciliation

Each input range declares a `basis` and `role` (`model_implied`, `scenario`, `market_anchor`, `cross_check`). Only compatible model-implied ranges may produce a mathematical intersection. Non-overlap returns `MODEL_DISAGREEMENT`; incompatible bases return `NOT_COMPARABLE`; cross-check inputs remain explicitly cross-checks.

## 5. Verification

- Unit tests prove each typed contract and every fail-closed branch.
- Integration tests compare semantic fingerprints at result, view and document boundaries.
- Architecture tests reject version strings as analytical rationales and company-specific production logic.
- Historical field replays v1.5.08–v1.5.11 remain green.
- v1.5.12 runs both an anonymous manufacturing fixture and the PIT steel-superalloy field case.
