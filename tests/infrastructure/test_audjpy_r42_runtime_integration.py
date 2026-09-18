from __future__ import annotations

import ast
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.r42_audjpy_live import (
    CERTIFICATION_IDENTITY,
    IDENTITY,
    MEMORY_SHA256,
)


RUNTIME = Path("scripts/qore_fundednext_runtime.py")


def _runtime_text() -> str:
    return RUNTIME.read_text(encoding="utf-8")


def test_runtime_source_parses_and_keeps_single_resident_entrypoint() -> None:
    tree = ast.parse(_runtime_text())
    mains = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    ]
    assert len(mains) == 1


def test_runtime_started_contains_all_six_certified_traders() -> None:
    text = _runtime_text()
    for trader in (
        "VT08",
        "TURTLE_SOUP_XAUUSD_R34",
        "TURTLE_SOUP_EURUSD_R38",
        "TURTLE_SOUP_GBPUSD_R43",
        "TURTLE_SOUP_GBPJPY_R38",
        "TURTLE_SOUP_AUDJPY_R42",
    ):
        assert f'"{trader}"' in text
    assert '"single_mt5_writer": True' in text
    assert '"account_wide_risk_active": True' in text


def test_audjpy_runtime_uses_sovereign_risk_and_no_parallel_gateway() -> None:
    text = _runtime_text()
    assert "build_r42_audjpy_risk_request" in text
    assert "_process_audjpy_r42_candidate" in text
    assert "risk.authorize(request, snapshot, now=now)" in text
    assert "gateway.shadow_check(submission, now=now)" in text
    assert text.count("FundedNextLiveMt5ExecutionGateway(") == 1
    assert TraderLineage.R42_AUDJPY.value == "R42_AUDJPY"


def test_audjpy_runtime_binds_certified_identity_and_memory() -> None:
    text = _runtime_text()
    assert IDENTITY == "TURTLE_SOUP_AUDJPY_R42"
    assert CERTIFICATION_IDENTITY == (
        "TURTLE_SOUP_AUDJPY_R43_FINAL_CERTIFICATION_SUITE_V1"
    )
    assert MEMORY_SHA256 == (
        "22cc9fbccb8d88fe5e5027c93d93412b3cee3f9e724dae034ff9f56a0e82cfe6"
    )
    assert '"audjpy_r42_memory_sha256": "' + MEMORY_SHA256 + '"' in text


def test_shadow_position_management_is_no_send_for_audjpy() -> None:
    text = _runtime_text()
    assert "manage_audjpy_r42_open_position(" in text
    assert "mutations_enabled=mode == \"live\"" in text
    assert 'if mode == "shadow":' in text


def test_audjpy_has_independent_state_and_processed_anchor() -> None:
    text = _runtime_text()
    assert '"r42-audjpy-state.json"' in text
    assert 'f"R42_AUDJPY|{audjpy_r42_anchor.isoformat()}"' in text
    assert "audjpy_r42_store" in text
    assert "audjpy_r42_memory" in text

# Frozen-base CI trigger v3.
