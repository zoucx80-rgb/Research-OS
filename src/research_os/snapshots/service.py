"""Build and persist immutable Snapshot Schema 2.0 envelopes."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from research_os.application.command import ResearchRunCommand
from research_os.application.repositories import ResearchRun, UnitOfWork
from research_os.application.result import ResearchRunResult, ResearchSnapshotDescriptor
from research_os.contracts.errors import PersistenceError
from research_os.snapshots.codec import SnapshotCodecV2
from research_os.snapshots.models import (
    ArtifactFingerprint,
    ResearchSnapshotPayloadV2,
    ResearchSnapshotV2,
    SnapshotArtifactV2,
)


UnitOfWorkFactory = Callable[[], AbstractContextManager[UnitOfWork]]


def _freeze_assumption(value: object) -> object:
    if isinstance(value, Enum):
        return _freeze_assumption(value.value)
    if isinstance(value, BaseModel):
        return MappingProxyType(
            {
                field_name: _freeze_assumption(getattr(value, field_name))
                for field_name in type(value).model_fields
            }
        )
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise PersistenceError("research input mappings must use string keys")
        return MappingProxyType(
            {key: _freeze_assumption(item) for key, item in value.items()}
        )
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_assumption(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_assumption(item) for item in value)
    return value


def _semantic_inputs(command: ResearchRunCommand) -> tuple[object, ...]:
    """Freeze only inputs that can influence research semantics.

    Persistence is an output-side concern and must never change the research digest.
    Plugin selection controls and external-version identities remain semantic because
    they can change the implementation or evidence interpretation used by the run.
    """

    domain_fields = tuple(
        MappingProxyType({field_name: _freeze_assumption(getattr(command, field_name))})
        for field_name in (
            "financial",
            "thesis",
            "expectations",
            "valuation",
            "monitoring",
            "forecasting",
            "peers",
            "readiness",
        )
    )
    options = command.options
    semantic_options = MappingProxyType(
        {
            "industry_plugin_override": _freeze_assumption(
                options.industry_plugin_override
            ),
            "methodology_plugin_overrides": _freeze_assumption(
                options.methodology_plugin_overrides
            ),
            "override_rationale": _freeze_assumption(options.override_rationale),
            "allow_experimental_plugins": options.allow_experimental_plugins,
            "external_versions": _freeze_assumption(options.external_versions),
        }
    )
    return (*domain_fields, MappingProxyType({"options": semantic_options}))


class SnapshotVerification(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid: bool
    reason: str | None = None


class SnapshotService:
    def __init__(
        self,
        *,
        codec: SnapshotCodecV2 | None = None,
        clock: Callable[[], datetime] | None = None,
        snapshot_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._codec = codec or SnapshotCodecV2()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._snapshot_id_factory = snapshot_id_factory or (lambda: str(uuid4()))

    def build(
        self,
        *,
        command: ResearchRunCommand,
        result: ResearchRunResult,
    ) -> ResearchSnapshotV2:
        envelopes = result.artifacts.envelopes()
        artifacts = tuple(
            SnapshotArtifactV2(
                artifact_id=envelope.key.artifact_id,
                schema_version=envelope.key.schema_version,
                type_id=envelope.key.value_type.__qualname__,
                producer_ids=envelope.producer_ids,
                evidence_refs=envelope.evidence_refs,
                payload=envelope.value,
            )
            for envelope in envelopes
        )
        artifact_fingerprints = tuple(
            ArtifactFingerprint(
                artifact_id=envelope.key.artifact_id,
                schema_version=envelope.key.schema_version,
                type_id=envelope.key.value_type.__qualname__,
                value_fingerprint=envelope.value_fingerprint,
            )
            for envelope in envelopes
        )
        payload = ResearchSnapshotPayloadV2(
            company=result.company,
            decision_ts=result.decision_ts,
            baseline=result.baseline,
            versions=result.versions,
            component_fingerprints=result.component_fingerprints,
            artifacts=artifacts,
            input_assumptions=_semantic_inputs(command),
            execution_completion=result.execution_completion,
            research_readiness=result.research_readiness,
        )
        research_digest = self._codec.research_digest(payload)
        snapshot = ResearchSnapshotV2(
            snapshot_id=self._snapshot_id_factory(),
            schema_version="2.0",
            codec_version=self._codec.codec_version,
            hash_algorithm="sha256",
            run_id=result.run_id,
            company_id=result.company.company_id,
            decision_ts=result.decision_ts,
            created_at=self._utc_now(),
            baseline=result.baseline,
            versions=result.versions,
            component_fingerprints=result.component_fingerprints,
            artifact_fingerprints=artifact_fingerprints,
            payload=payload,
            payload_hash=research_digest,
        )
        return snapshot

    def describe(self, snapshot: ResearchSnapshotV2) -> ResearchSnapshotDescriptor:
        return ResearchSnapshotDescriptor(
            snapshot_id=snapshot.snapshot_id,
            research_digest=snapshot.payload_hash,
            integrity_digest=self._codec.integrity_digest(snapshot),
        )

    def persist(
        self,
        *,
        command: ResearchRunCommand,
        result: ResearchRunResult,
        unit_of_work_factory: UnitOfWorkFactory,
    ) -> ResearchRunResult:
        snapshot = self.build(command=command, result=result)
        run = ResearchRun(
            run_id=result.run_id,
            company_id=result.company.company_id,
            decision_ts=result.decision_ts,
            created_at=snapshot.created_at,
            baseline=result.baseline,
            versions=result.versions,
            payload_json=json.dumps(
                {"snapshot_id": snapshot.snapshot_id},
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
        try:
            with unit_of_work_factory() as unit_of_work:
                unit_of_work.runs.append(run)
                unit_of_work.snapshots.append(snapshot)
                unit_of_work.commit()
        except Exception as exc:
            raise PersistenceError(
                "research run and snapshot transaction failed",
                context={"run_id": result.run_id, "snapshot_id": snapshot.snapshot_id},
            ) from exc
        descriptor = self.describe(snapshot)
        return result.model_copy(update={"snapshot": descriptor})

    def verify(
        self,
        snapshot: ResearchSnapshotV2,
        *,
        integrity_digest: str,
    ) -> SnapshotVerification:
        research_digest = self._codec.research_digest(snapshot.payload)
        if research_digest != snapshot.payload_hash:
            return SnapshotVerification(valid=False, reason="research digest mismatch")
        if self._codec.integrity_digest(snapshot) != integrity_digest:
            return SnapshotVerification(valid=False, reason="integrity digest mismatch")
        return SnapshotVerification(valid=True)

    def _utc_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise PersistenceError("snapshot clock must return a timezone-aware datetime")
        return value.astimezone(timezone.utc)
