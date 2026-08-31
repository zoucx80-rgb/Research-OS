from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
import re


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SourcePin:
    """Expected source identity for a fail-closed historical runtime dependency."""

    module_name: str
    sha256: str

    def __post_init__(self) -> None:
        if not self.module_name.strip():
            raise ValueError("source pin module_name must not be blank")
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("source pin sha256 must be lowercase SHA-256 hex")


@dataclass(frozen=True)
class SourceTreePin:
    """Expected identity for every Python source in a runtime package tree."""

    package_name: str
    sha256: str
    excluded_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.package_name.strip():
            raise ValueError("source tree pin package_name must not be blank")
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("source tree pin sha256 must be lowercase SHA-256 hex")
        invalid_paths = [
            path
            for path in self.excluded_paths
            if not path.strip() or Path(path).is_absolute() or ".." in Path(path).parts
        ]
        if invalid_paths:
            raise ValueError("source tree pin exclusions must be relative package paths")


def _load_module_source(module_name: str) -> bytes:
    spec = find_spec(module_name)
    origin = getattr(spec, "origin", None) if spec is not None else None
    if not origin or not origin.endswith(".py"):
        raise RuntimeError(f"cannot resolve pinned Python source: {module_name}")
    return Path(origin).read_bytes()


def load_source_tree_digest(
    path: Path,
    *,
    text_loader: Callable[[Path], str] = Path.read_text,
) -> str:
    """Load a digest from a non-executable resource with strict framing."""

    content = text_loader(path)
    candidate = content.rstrip("\r\n")
    if content not in {candidate, candidate + "\n", candidate + "\r\n"} or not (
        _SHA256.fullmatch(candidate)
    ):
        raise RuntimeError(f"invalid frozen source tree digest: {path}")
    return candidate


def _package_root(package_name: str) -> Path:
    spec = find_spec(package_name)
    locations = list(getattr(spec, "submodule_search_locations", ()) or ())
    if len(locations) != 1:
        raise RuntimeError(f"cannot resolve pinned Python package: {package_name}")
    return Path(locations[0])


def source_tree_fingerprint(
    package_name: str,
    *,
    excluded_paths: Iterable[str] = (),
    source_loader: Callable[[Path], bytes] = Path.read_bytes,
) -> str:
    """Hash relative paths and contents for all Python sources in a package tree."""

    package_root = _package_root(package_name)
    excluded = set(excluded_paths)
    source_paths = sorted(
        (
            path
            for path in package_root.rglob("*.py")
            if path.relative_to(package_root).as_posix() not in excluded
        ),
        key=lambda path: path.relative_to(package_root).as_posix(),
    )
    if not source_paths:
        raise RuntimeError(f"no pinned Python sources found: {package_name}")

    digest = sha256()
    for path in source_paths:
        relative_path = path.relative_to(package_root).as_posix().encode("utf-8")
        content = source_loader(path)
        digest.update(len(relative_path).to_bytes(8, "big"))
        digest.update(relative_path)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def validate_source_pins(
    pins: Iterable[SourcePin],
    *,
    source_loader: Callable[[str], bytes] = _load_module_source,
) -> None:
    """Reject historical replay when a pinned implementation has drifted."""

    mismatches: list[str] = []
    for pin in pins:
        actual = sha256(source_loader(pin.module_name)).hexdigest()
        if actual != pin.sha256:
            mismatches.append(pin.module_name)
    if mismatches:
        raise RuntimeError(
            "frozen runtime source drift: " + ", ".join(sorted(mismatches))
        )


def validate_source_tree_pin(
    pin: SourceTreePin,
    *,
    source_loader: Callable[[Path], bytes] = Path.read_bytes,
) -> None:
    """Reject historical replay when any package source has drifted."""

    actual = source_tree_fingerprint(
        pin.package_name,
        excluded_paths=pin.excluded_paths,
        source_loader=source_loader,
    )
    if actual != pin.sha256:
        raise RuntimeError(f"frozen runtime source tree drift: {pin.package_name}")
