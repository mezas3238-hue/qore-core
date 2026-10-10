from qore.infrastructure.trader_lab.vt08_cognitive_eurjpy_5y_failure_forensics_v1 import (
    AXES,
    MARKET,
)


def test_eurjpy_5y_forensics_is_diagnostics_scope() -> None:
    assert MARKET == "EURJPY"
    assert "anchor" in AXES
    assert "risk_ref_band" in AXES
