# Research OS v1.1 Evidence & Versioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the immutable evidence model, PIT retrieval, version bundle, and frozen research snapshot required by every v1.1 subsystem.

**Architecture:** Use Pydantic domain objects at service boundaries and SQLAlchemy models for persistence. PIT selection is centralized in one repository method so no downstream feature can accidentally use `period_end` as information availability time.

**Tech Stack:** Python 3.12+, Pydantic v2, SQLAlchemy 2.x, PostgreSQL, Alembic, pytest.

**Spec:** `/mnt/data/Research_OS_v1.1_完整规范.md`

## Global Constraints

- `publish_ts` determines information availability.
- Raw evidence revisions are append-only.
- Confidence grades are exactly A/B/C/D/E.
- Snapshot version metadata is immutable after freeze.
- Missing source fields remain null, never guessed.

---

### Task 1: Create the domain enums and Evidence object

**Files:**
- Create: `src/research_os/domain/enums.py`
- Create: `src/research_os/domain/evidence.py`
- Test: `tests/unit/domain/test_evidence.py`

**Interfaces:**
- Produces: `ConfidenceGrade`, `VerificationStatus`, `EvidenceType`, `Evidence`.
- Consumes: none.

- [ ] **Step 1: Write the failing enum/model test**

```python
from datetime import datetime, timezone
from research_os.domain.enums import ConfidenceGrade, VerificationStatus
from research_os.domain.evidence import Evidence

def test_evidence_keeps_period_and_publish_time_separate():
    e = Evidence(
        evidence_id="e1",
        company_id="001287.SZ",
        evidence_type="filing_fact",
        period_end="2026-06-30",
        publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 8, 25, 1, tzinfo=timezone.utc),
        value=735.56,
        unit="CNY_100M",
        confidence_grade=ConfidenceGrade.A,
        verification_status=VerificationStatus.PRIMARY_VERIFIED,
    )
    assert e.period_end.isoformat() == "2026-06-30"
    assert e.publish_ts.date().isoformat() == "2026-08-25"
```

- [ ] **Step 2: Run the test and verify import failure**

Run: `pytest tests/unit/domain/test_evidence.py -v`  
Expected: FAIL because `research_os.domain.evidence` does not exist.

- [ ] **Step 3: Implement exact enums**

```python
from enum import StrEnum

class ConfidenceGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"

class VerificationStatus(StrEnum):
    PRIMARY_VERIFIED = "PRIMARY_VERIFIED"
    SECONDARY_VERIFIED = "SECONDARY_VERIFIED"
    SECONDARY_UNVERIFIED = "SECONDARY_UNVERIFIED"
    ESTIMATED = "ESTIMATED"
    ASSUMPTION = "ASSUMPTION"

class EvidenceType(StrEnum):
    FILING_FACT = "filing_fact"
    MARKET_DATA = "market_data"
    CONSENSUS = "consensus"
    MANAGEMENT_STATEMENT = "management_statement"
    INDUSTRY_DATA = "industry_data"
    CALCULATED_METRIC = "calculated_metric"
    STATISTICAL_RESULT = "statistical_result"
    ANALYST_ASSUMPTION = "analyst_assumption"
```

- [ ] **Step 4: Implement the Pydantic Evidence model**

```python
from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict
from .enums import ConfidenceGrade, EvidenceType, VerificationStatus

class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    company_id: str
    evidence_type: EvidenceType
    period_end: date | None = None
    publish_ts: datetime
    ingested_at: datetime
    value: Any = None
    unit: str | None = None
    scope: str | None = None
    source_document_id: str | None = None
    source_page: int | None = None
    source_table: str | None = None
    source_url: str | None = None
    confidence_grade: ConfidenceGrade
    verification_status: VerificationStatus
    dataset_version: str | None = None
    parser_version: str | None = None
    formula_version: str | None = None
    model_version: str | None = None
    revision_no: int = 1
```

- [ ] **Step 5: Run the unit test**

Run: `pytest tests/unit/domain/test_evidence.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/research_os/domain tests/unit/domain
git commit -m "feat: add immutable evidence domain model"
```

### Task 2: Add SQL persistence and append-only revision rules

**Files:**
- Create: `src/research_os/storage/db.py`
- Create: `src/research_os/storage/models.py`
- Create: `alembic/versions/0001_evidence.py`
- Test: `tests/integration/storage/test_evidence_store.py`

**Interfaces:**
- Produces: `EvidenceRow`, `EvidenceStore.append()`, `EvidenceStore.as_of()`.
- Consumes: `Evidence`.

- [ ] **Step 1: Write a failing PIT integration test**

```python
def test_as_of_excludes_future_publication(evidence_store, sample_evidence):
    evidence_store.append(sample_evidence(publish_ts="2026-08-25T00:00:00+00:00"))
    rows = evidence_store.as_of("001287.SZ", decision_ts="2026-08-24T23:59:59+00:00")
    assert rows == []
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/integration/storage/test_evidence_store.py::test_as_of_excludes_future_publication -v`  
Expected: FAIL because `EvidenceStore` is missing.

- [ ] **Step 3: Implement append and PIT query**

```python
from datetime import datetime
from sqlalchemy import select

class EvidenceStore:
    def __init__(self, session):
        self.session = session

    def append(self, evidence: Evidence) -> None:
        self.session.add(EvidenceRow.from_domain(evidence))
        self.session.flush()

    def as_of(self, company_id: str, decision_ts: datetime) -> list[Evidence]:
        stmt = (
            select(EvidenceRow)
            .where(EvidenceRow.company_id == company_id)
            .where(EvidenceRow.publish_ts <= decision_ts)
            .order_by(EvidenceRow.publish_ts, EvidenceRow.revision_no)
        )
        return [row.to_domain() for row in self.session.scalars(stmt)]
```

- [ ] **Step 4: Add an append-only uniqueness constraint**

Migration must create a unique key on:

```text
(evidence_id, revision_no)
```

and must not define an UPDATE-based correction path.

- [ ] **Step 5: Add revision preservation test**

```python
def test_correction_creates_new_revision(evidence_store, sample_evidence):
    evidence_store.append(sample_evidence(evidence_id="rev", revision_no=1, value=10))
    evidence_store.append(sample_evidence(evidence_id="rev", revision_no=2, value=12))
    rows = evidence_store.as_of("001287.SZ", decision_ts="2026-12-31T00:00:00+00:00")
    assert [r.value for r in rows if r.evidence_id == "rev"] == [10, 12]
```

- [ ] **Step 6: Run integration tests**

Run: `pytest tests/integration/storage/test_evidence_store.py -v`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/research_os/storage alembic/versions/0001_evidence.py tests/integration/storage
git commit -m "feat: add point-in-time evidence store"
```

### Task 3: Implement VersionBundle and frozen ResearchSnapshot

**Files:**
- Create: `src/research_os/domain/versions.py`
- Create: `src/research_os/snapshots/service.py`
- Create: `alembic/versions/0002_research_snapshot.py`
- Test: `tests/unit/snapshots/test_snapshot_service.py`

**Interfaces:**
- Produces: `VersionBundle`, `ResearchSnapshot`, `SnapshotService.freeze()`.
- Consumes: company ID, decision timestamp, version strings.

- [ ] **Step 1: Write the failing freeze test**

```python
def test_freeze_persists_all_required_versions(snapshot_service):
    snapshot = snapshot_service.freeze(
        company_id="001287.SZ",
        decision_ts="2026-08-29T08:00:00+00:00",
        versions={
            "research_os_version": "1.1.0",
            "dataset_version": "2026-08-29.1",
            "parser_version": "parser@1.0.0",
            "formula_version": "finance-core@2.0.0",
            "router_version": "router@1.0.0",
            "kpi_pack_version": "distributor@1.0.0",
            "driver_model_version": "drivers@1.0.0",
            "forecast_version": "forecast@1.0.0",
            "valuation_version": "valuation@2.0.0",
            "report_version": "report@3.0.0",
        },
    )
    assert snapshot.versions.research_os_version == "1.1.0"
```

- [ ] **Step 2: Run and verify failure**

Run: `pytest tests/unit/snapshots/test_snapshot_service.py -v`  
Expected: FAIL because snapshot service is missing.

- [ ] **Step 3: Implement VersionBundle**

```python
from pydantic import BaseModel, ConfigDict

class VersionBundle(BaseModel):
    model_config = ConfigDict(frozen=True)
    research_os_version: str
    dataset_version: str
    parser_version: str
    formula_version: str
    router_version: str
    kpi_pack_version: str
    driver_model_version: str
    forecast_version: str
    valuation_version: str
    report_version: str
```

- [ ] **Step 4: Implement snapshot freeze**

`SnapshotService.freeze()` must insert once and reject mutation of an existing `snapshot_id`.

- [ ] **Step 5: Add mutation rejection test**

```python
def test_frozen_snapshot_is_not_mutable(snapshot_service, frozen_snapshot):
    with pytest.raises(SnapshotFrozenError):
        snapshot_service.replace_versions(frozen_snapshot.snapshot_id, {"report_version": "x"})
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/unit/snapshots/test_snapshot_service.py -v`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/research_os/domain/versions.py src/research_os/snapshots alembic/versions/0002_research_snapshot.py tests/unit/snapshots
git commit -m "feat: freeze reproducible research snapshots"
```

### Task 4: Add foundation quality gates

**Files:**
- Create: `tests/golden/test_no_time_travel.py`
- Create: `tests/golden/test_raw_revision_preservation.py`
- Modify: `pyproject.toml`
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: CI gate for PIT and immutability.
- Consumes: EvidenceStore and SnapshotService.

- [ ] **Step 1: Add the no-lookahead property test**

```python
from hypothesis import given, strategies as st

@given(
    publish_offset=st.integers(min_value=1, max_value=365),
)
def test_future_evidence_never_enters_asof_snapshot(publish_offset, store, base_date):
    publish_ts = base_date + timedelta(days=publish_offset)
    store.append(make_evidence(publish_ts=publish_ts))
    assert store.as_of("001287.SZ", base_date) == []
```

- [ ] **Step 2: Run golden tests**

Run: `pytest tests/golden/test_no_time_travel.py tests/golden/test_raw_revision_preservation.py -v`  
Expected: PASS.

- [ ] **Step 3: Add CI commands**

```yaml
- run: ruff check .
- run: mypy src
- run: pytest tests/unit -q
- run: pytest tests/integration -q
- run: pytest tests/golden -q
```

- [ ] **Step 4: Run the full local gate**

Run: `ruff check . && mypy src && pytest -q`  
Expected: all commands succeed.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .github/workflows/ci.yml tests/golden
git commit -m "test: gate point-in-time evidence foundation"
```
