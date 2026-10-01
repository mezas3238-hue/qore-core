from decimal import Decimal

from scripts.cibo_t16_ctrader_demo_post_declaration_probe import (
    _canonical,
    _digest,
)


def test_t16_probe_canonicalizes_decimal_without_promoting_costs() -> None:
    payload = _canonical(
        {
            "spread_bps": Decimal("1.2500"),
            "realized_slippage_observed": False,
            "full_hedge_cost_model_ready": False,
        }
    )

    assert payload == {
        "full_hedge_cost_model_ready": False,
        "realized_slippage_observed": False,
        "spread_bps": "1.2500",
    }
    assert _digest(payload).startswith("sha256:")
