"""Verify conservative AST provenance: positive callers never imply live admission."""

from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.capitalizer_scalper_caller_audit_v1 import (
    IDENTITY,
    audit_callers,
)


def _source(root: Path, relative: str, content: str) -> None:
    file = root / relative
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")


def test_finds_aliased_import_and_qualified_module_calls(tmp_path: Path) -> None:
    _source(
        tmp_path,
        "pkg/strategy.py",
        "def strict() -> None:\n    return None\n",
    )
    _source(
        tmp_path,
        "pkg/replay.py",
        (
            "from pkg.strategy import strict as strict_gate\n"
            "import pkg.strategy as source\n\n"
            "def run() -> None:\n"
            "    strict_gate()\n"
            "    source.strict()\n"
        ),
    )
    report = audit_callers(
        tmp_path,
        targets=("pkg.strategy.strict",),
        roots=("pkg.replay.run",),
    )
    assert report.identity == IDENTITY
    assert report.source_files_scanned == 2
    assert report.targets[0].classification == (
        "REACHABLE_FROM_SELECTED_RESEARCH_ENTRYPOINT"
    )
    assert report.targets[0].root_reachable is True
    assert tuple(item.line for item in report.targets[0].static_call_sites) == (5, 6)
    assert report.can_certify_source_fidelity is False
    assert report.can_authorize_execution is False


def test_missing_direct_caller_remains_unresolved_not_dead(tmp_path: Path) -> None:
    _source(
        tmp_path,
        "pkg/strategy.py",
        (
            "def strict() -> None:\n"
            "    return None\n"
            "def runtime(obj: object) -> object:\n"
            "    return getattr(obj, 'strict')()\n"
        ),
    )
    result = audit_callers(tmp_path, targets=("pkg.strategy.strict",))
    assert result.targets[0].classification == (
        "NO_STATIC_CALLER_FOUND_RUNTIME_UNRESOLVED"
    )
    assert result.targets[0].static_call_sites == ()
    assert "pkg/strategy.py:4:getattr" in result.dynamic_call_sites


def test_strict_gate_caller_outside_selected_entrypoint_not_marked_enforced(
    tmp_path: Path,
) -> None:
    _source(
        tmp_path,
        "pkg/strategy.py",
        "def strict() -> None:\n    return None\n",
    )
    _source(
        tmp_path,
        "pkg/diagnostic.py",
        (
            "from pkg.strategy import strict\n\n"
            "def research_report() -> None:\n    strict()\n"
        ),
    )
    result = audit_callers(
        tmp_path,
        targets=("pkg.strategy.strict",),
        roots=("pkg.replay.build_market",),
    )
    assert result.targets[0].classification == (
        "STATIC_CALLER_FOUND_OUTSIDE_SELECTED_ENTRYPOINT"
    )


def test_absent_source_tree_is_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no Python modules"):
        audit_callers(tmp_path)
