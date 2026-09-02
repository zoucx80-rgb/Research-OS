from research_os.application.result import ResearchSnapshotDescriptor
from research_os.snapshots.models import (
    ArtifactFingerprint,
    ResearchSnapshotPayloadV2,
    ResearchSnapshotV2,
    SnapshotArtifactV2,
)

__all__ = [
    "ArtifactDecoderRegistry",
    "ArtifactFingerprint",
    "ResearchSnapshotDescriptor",
    "ResearchSnapshotPayloadV2",
    "ResearchSnapshotV2",
    "SnapshotArtifactV2",
    "SnapshotCodecError",
    "SnapshotCodecV2",
    "build_core_artifact_decoder_registry",
]


def __getattr__(name: str) -> object:
    if name in {
        "ArtifactDecoderRegistry",
        "SnapshotCodecError",
        "SnapshotCodecV2",
        "build_core_artifact_decoder_registry",
    }:
        from research_os.snapshots import codec

        return getattr(codec, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
