import re

from .models import RepositoryPreflightEvidence, PreflightValidationResult


OFFICIAL_REPOSITORY = "zoucx80-rgb/Research-OS"
OFFICIAL_REPOSITORY_ID = 1350382205
OFFICIAL_BRANCH = "main"
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def _is_placeholder_sha(value: str) -> bool:
    value = value.lower()
    if not _GIT_SHA.fullmatch(value):
        return True
    if len(set(value)) <= 4:
        return True
    if value.startswith(("abcdefabcdef", "deadbeefdead", "0123456789012345")):
        return True
    for width in range(1, 11):
        pattern = value[:width]
        repeated = (pattern * ((40 // width) + 1))[:40]
        if repeated == value:
            return True
    return False


class PreflightValidator:
    def validate(self, evidence: RepositoryPreflightEvidence) -> PreflightValidationResult:
        if evidence.repository_full_name != OFFICIAL_REPOSITORY:
            raise ValueError("repository full name mismatch")
        if evidence.repository_id != OFFICIAL_REPOSITORY_ID:
            raise ValueError("repository id mismatch")
        if evidence.branch != OFFICIAL_BRANCH:
            raise ValueError("repository branch mismatch")

        for label, sha in (
            ("head", evidence.head_sha),
            ("AGENTS blob", evidence.agents_blob_sha),
            ("research prompt blob", evidence.research_prompt_blob_sha),
        ):
            if _is_placeholder_sha(sha):
                raise ValueError(f"{label} SHA is invalid or placeholder")

        if (
            evidence.agents_ref != evidence.head_sha
            or evidence.research_prompt_ref != evidence.head_sha
        ):
            raise ValueError("required files must be read from frozen HEAD")
        if not evidence.head_commit_message.strip():
            raise ValueError("head commit message is required")

        return PreflightValidationResult(
            repository_full_name=evidence.repository_full_name,
            repository_id=evidence.repository_id,
            branch=evidence.branch,
            head_sha=evidence.head_sha,
        )
