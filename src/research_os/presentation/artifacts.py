from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
import re
from typing import Any, Literal, Mapping, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research_os.reporting import ResearchReportDocument


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _text_hash(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("canonical document hashing rejects non-finite numeric values")
    if isinstance(value, dict):
        for item in value.values():
            _reject_non_finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_non_finite(item)


def canonical_document_hash(document: ResearchReportDocument) -> str:
    if not isinstance(document, ResearchReportDocument):
        raise TypeError("canonical_document_hash requires ResearchReportDocument")
    _reject_non_finite(document.model_dump(mode="python"))
    try:
        payload = json.dumps(
            document.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except ValueError as exc:
        raise ValueError("canonical document hashing rejects non-finite numeric values") from exc
    return _text_hash(payload)


class _PresentationArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    renderer_version: str = Field(min_length=1)
    source_hash: str
    content_hash: str

    @field_validator("source_hash", "content_hash")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("artifact hashes must be lowercase SHA-256 hex")
        return value

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        payload = self.model_dump(mode="python")
        if deep:
            payload = deepcopy(payload)
        if update:
            payload.update(update)
        return self.__class__.model_validate(payload)


class MarkdownPresentationArtifact(_PresentationArtifact):
    artifact_type: Literal["markdown"] = "markdown"
    media_type: Literal["text/markdown; charset=utf-8"] = "text/markdown; charset=utf-8"
    content: str

    @model_validator(mode="after")
    def _content_hash_matches(self) -> Self:
        if self.content_hash != _text_hash(self.content):
            raise ValueError("Markdown content_hash does not match content")
        return self

    @classmethod
    def from_document(
        cls,
        *,
        document: ResearchReportDocument,
        renderer_version: str,
        content: str,
    ) -> Self:
        return cls(
            renderer_version=renderer_version,
            source_hash=canonical_document_hash(document),
            content_hash=_text_hash(content),
            content=content,
        )


class HtmlPresentationArtifact(_PresentationArtifact):
    artifact_type: Literal["html"] = "html"
    media_type: Literal["text/html; charset=utf-8"] = "text/html; charset=utf-8"
    style_hash: str
    content: str

    @field_validator("style_hash")
    @classmethod
    def _validate_style_hash(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("style_hash must be lowercase SHA-256 hex")
        return value

    @model_validator(mode="after")
    def _hashes_match_content(self) -> Self:
        if self.content_hash != _text_hash(self.content):
            raise ValueError("HTML content_hash does not match content")
        style_tags = re.findall(r"<style\b[^>]*>", self.content, flags=re.IGNORECASE)
        embedded_styles = re.findall(
            r"<style>(.*?)</style>",
            self.content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if len(style_tags) != 1 or len(embedded_styles) != 1:
            raise ValueError("HTML must embed exactly one plain style element")
        if self.style_hash != _text_hash(embedded_styles[0]):
            raise ValueError("HTML style_hash does not match embedded style")
        return self

    @classmethod
    def from_markdown(
        cls,
        *,
        markdown: MarkdownPresentationArtifact,
        renderer_version: str,
        style: str,
        content: str,
    ) -> Self:
        if not isinstance(markdown, MarkdownPresentationArtifact):
            raise TypeError("HtmlPresentationArtifact requires MarkdownPresentationArtifact")
        return cls(
            renderer_version=renderer_version,
            source_hash=markdown.content_hash,
            content_hash=_text_hash(content),
            style_hash=_text_hash(style),
            content=content,
        )


class PdfPresentationArtifact(_PresentationArtifact):
    artifact_type: Literal["pdf"] = "pdf"
    media_type: Literal["application/pdf"] = "application/pdf"
    backend_version: str = Field(min_length=1)
    content: bytes

    @model_validator(mode="after")
    def _content_hash_matches(self) -> Self:
        if self.content_hash != sha256(self.content).hexdigest():
            raise ValueError("PDF content_hash does not match content")
        if not self.content.startswith(b"%PDF-"):
            raise ValueError("PDF content must start with a PDF signature")
        return self

    @classmethod
    def from_html(
        cls,
        *,
        html: HtmlPresentationArtifact,
        renderer_version: str,
        backend_version: str,
        content: bytes,
    ) -> Self:
        if not isinstance(html, HtmlPresentationArtifact):
            raise TypeError("PdfPresentationArtifact requires HtmlPresentationArtifact")
        return cls(
            renderer_version=renderer_version,
            backend_version=backend_version,
            source_hash=html.content_hash,
            content_hash=sha256(content).hexdigest(),
            content=content,
        )
