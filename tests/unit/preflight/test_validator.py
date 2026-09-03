import importlib
import importlib.util
from datetime import datetime, timezone

import pytest


def _load(name: str):
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, f"missing required module {name}"
    return importlib.import_module(name)


def _valid_preflight():
    models = _load("research_os.preflight.models")
    return models.RepositoryPreflightEvidence(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        head_sha="8b23c6f8196a5d96aa3ebc19d9f4ecb4a05532c2",
        head_commit_message="docs: bind stock research shorthand to canonical protocol",
        agents_blob_sha="02ba8f81430e68121ef5c98b49a3ecfcc103fc5e",
        research_prompt_blob_sha="3210dc567ae25653ea80c3911481e2b0d2864f69",
        verified_at=datetime(2026, 8, 29, tzinfo=timezone.utc),
        agents_ref="8b23c6f8196a5d96aa3ebc19d9f4ecb4a05532c2",
        research_prompt_ref="8b23c6f8196a5d96aa3ebc19d9f4ecb4a05532c2",
    )


def test_preflight_accepts_exact_frozen_repository_identity():
    validator = _load("research_os.preflight.validator").PreflightValidator()
    assert validator.validate(_valid_preflight()).status == "PASS"


def test_placeholder_sha_is_rejected():
    validator = _load("research_os.preflight.validator").PreflightValidator()
    item = _valid_preflight().model_copy(
        update={"head_sha": "abcdefabcdefabcdefabcdefabcdefabcdef1234"}
    )
    with pytest.raises(ValueError, match="placeholder"):
        validator.validate(item)


def test_preflight_file_must_be_read_from_frozen_head():
    validator = _load("research_os.preflight.validator").PreflightValidator()
    item = _valid_preflight().model_copy(update={"agents_ref": "main"})
    with pytest.raises(ValueError, match="frozen HEAD"):
        validator.validate(item)


def test_repository_identity_mismatch_is_rejected():
    validator = _load("research_os.preflight.validator").PreflightValidator()
    item = _valid_preflight().model_copy(update={"repository_id": 1})
    with pytest.raises(ValueError, match="repository"):
        validator.validate(item)
