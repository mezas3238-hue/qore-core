from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r64_canonical_economic_binding as r64,
)
from qore.infrastructure.traders import vt08_index_specialist_contract as specialist


def test_r64_is_bound_to_r63_specialist_contract() -> None:
    assert r64.specialist.CONFIG_FINGERPRINT == (
        "e959c8578a7ac71658cd19daf6d61815dfe277ecd06d8100c2655b30a62f48fa"
    )
    assert specialist.CANDIDATE_ID == r64.freeze.CANDIDATE_ID
    assert specialist.FREEZE_ID == r64.freeze.FREEZE_ID


def test_r64_preserves_three_market_scope() -> None:
    assert specialist.MARKETS == ("NAS100", "SP500", "US30")
    assert specialist.TIMEFRAMES == ("M15", "H4")
    assert specialist.PORTFOLIO_INSTRUMENT == "VT08INDEX"


def test_r64_reconciles_frozen_secondary_contract() -> None:
    assert r64.SECONDARY_STRESS == Decimal("0.10")
    assert r64.EXPECTED_SAMPLE == 3465
    assert r64.EXPECTED_TOTAL_R == (
        Decimal(str(r64.freeze.FIVE_YEAR["secondary_total_r"]))
        + Decimal(str(r64.freeze.RECENT_TWO_YEAR["secondary_total_r"]))
    )
    assert r64.EXPECTED_TOTAL_R > Decimal("25")
