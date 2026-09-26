"""CIBO CMA sizing-authority telemetry invariants."""

from __future__ import annotations

from pathlib import Path

from qore.infrastructure.ctrader_demo_live_behavior_lab import sizing_path_for


ACTIVE = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)


def test_all_active_demo_traders_emit_cibo_cma_sizing_path() -> None:
    assert {
        sizing_path_for(trader)
        for trader in ACTIVE
    } == {"CIBO_CMA_MINIMAL_SEED"}


def test_sink_records_cibo_as_sizing_and_capital_authority() -> None:
    source = Path(
        "src/qore/infrastructure/ctrader_demo_free_sink.py"
    ).read_text(encoding="utf-8")

    assert '"sizing_authority": "CIBO_CMA"' in source
    assert '"capital_management_authority": "CIBO_CMA"' in source
