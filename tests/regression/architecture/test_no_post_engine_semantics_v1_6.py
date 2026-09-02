from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_application_service_has_no_post_engine_domain_semantic_calls():
    source = (ROOT / "src/research_os/application/service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {
        "ThesisService",
        "ExpectationValidator",
        "ValuationReconciler",
        "ResearchViewPresenter",
    }

    imported_or_called = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    }

    assert not forbidden & imported_or_called


def test_completion_and_readiness_are_finalized_inside_the_engine_boundary():
    source = (ROOT / "src/research_os/application/service.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert "evaluate" not in called_attributes
    assert "finalize" in called_attributes


def test_finalizer_does_not_import_artifact_writers_or_domain_services():
    source = (ROOT / "src/research_os/application/finalizer.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    assert not any(
        module.startswith(
            (
                "research_os.thesis",
                "research_os.expectations",
                "research_os.valuation",
                "research_os.contracts.artifacts",
            )
        )
        for module in imported_modules
    )
