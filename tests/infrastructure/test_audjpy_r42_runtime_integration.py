from __future__ import annotations

import ast
from datetime import timedelta
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.r42_audjpy_live import (
    CERTIFICATION_IDENTITY,
    ENTRY_SLA,
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
    assert "risk.authorize(request, snapshot, now=authorize_at)" in text
    assert "gateway.shadow_check(submission, now=shadow_at)" in text
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
    assert 'f"R42_AUDJPY|{audjpy_arm_anchor.isoformat()}"' in text
    assert "audjpy_r42_store" in text
    assert "audjpy_r42_memory" in text


def test_audjpy_runtime_hard_sla_prearms_before_maintenance() -> None:
    text = _runtime_text()
    assert "_LOOP_SECONDS = AUDJPY_R42_FEED_REFRESH_SECONDS" in text
    assert "audjpy_r42_cache = R42AudJpyM5Cache()" in text
    assert "audjpy_r42_cache.preload(mt5, now=datetime.now(UTC))" in text
    assert "audjpy_r42_cache.refresh_incremental(mt5, now=cycle_at)" in text
    assert "audjpy_r42_boundary_to_arm(cycle_at)" in text
    assert "await_audjpy_r42_boundary_snapshot(" in text
    assert '"event": "AUDJPY_R42_BOUNDARY_ARMED"' in text
    assert '"event": "AUDJPY_R42_SLA_FAIL_CLOSED"' in text
    assert "current_audjpy_r42_anchor" not in text
    critical = text.index("audjpy_arm_anchor = audjpy_r42_boundary_to_arm(cycle_at)")
    maintenance = text.index("account_state = gateway.read_account(now=cycle_at)")
    assert critical < maintenance


def test_audjpy_runtime_never_sends_after_deadline_guard() -> None:
    text = _runtime_text()
    guard = text.index('stage_time("before-order-send")')
    send = text.index("gateway.submit_live(submission, now=send_at)")
    assert guard < send
    assert "AUDJPY_R42_ENTRY_SLA" in text
    assert ENTRY_SLA == timedelta(seconds=10)
    assert '"order_send_called": False' in text


def test_audjpy_runtime_reports_24_7_and_latency_contract() -> None:
    text = _runtime_text()
    assert '"audjpy_r42_schedule": "EVERY_H1_H4_BOUNDARY_24_7_SERVICE"' in text
    assert '"audjpy_r42_history_preload_once": True' in text
    assert '"audjpy_r42_incremental_cache": True' in text
    assert '"audjpy_r42_boundary_retry_ms": 75' in text
