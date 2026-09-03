from __future__ import annotations

import hashlib
import json

from research_os.contracts.artifacts import ArtifactSnapshot


def semantic_projection(snapshot: ArtifactSnapshot) -> tuple[dict[str, object], ...]:
    """Project durable research semantics from typed Artifact envelopes only."""
    if not isinstance(snapshot, ArtifactSnapshot):
        raise TypeError("semantic_projection requires ArtifactSnapshot")
    return tuple(
        {
            "artifact_id": envelope.key.artifact_id,
            "schema_version": envelope.key.schema_version,
            "type_id": envelope.key.value_type.__qualname__,
            "producer_ids": list(envelope.producer_ids),
            "evidence_refs": [
                reference.model_dump(mode="json")
                for reference in envelope.evidence_refs
            ],
            "payload_fingerprint": envelope.value_fingerprint,
        }
        for envelope in snapshot.envelopes()
    )


def semantic_fingerprint(snapshot: ArtifactSnapshot) -> str:
    """Hash Artifact/Schema/provider/lineage/payload, excluding run/display identity."""
    payload = json.dumps(
        semantic_projection(snapshot),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = ["semantic_fingerprint", "semantic_projection"]
