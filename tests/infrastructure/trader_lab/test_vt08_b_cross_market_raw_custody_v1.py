"""VT08 B: market isolation regression for synthetic raw-bar receipts."""
from __future__ import annotations

import pytest
from test_vt08_b_situation_field_source_audit_v1 import RAW, _bundle

from qore.infrastructure.trader_lab.vt08_b_situation_field_source_audit_v1 import (
    verify_all_situation_field_receipts,
)


def test_foreign_raw_sha_rejected_despite_global_pin() -> None:
    situation, proofs, catalog = _bundle()
    with pytest.raises(ValueError, match="outside Situation market"):
        verify_all_situation_field_receipts(
            situation, proofs, catalog,
            pinned_raw_shas=frozenset((RAW, "b" * 64)),
            source_raw_market_map={RAW: situation.market, "b" * 64: "USDCHF"},
        )


def test_cross_market_bar_rejected_even_when_ohlc_digest_valid() -> None:
    situation, proofs, catalog = _bundle()
    next(iter(catalog.values()))["market"] = "USDCHF"
    with pytest.raises(ValueError, match="cross-market source bar"):
        verify_all_situation_field_receipts(
            situation, proofs, catalog,
            pinned_raw_shas=frozenset((RAW,)),
            source_raw_market_map={RAW: situation.market},
        )


def test_wrong_market_custody_rejected() -> None:
    situation, proofs, catalog = _bundle()
    with pytest.raises(ValueError, match="outside Situation market"):
        verify_all_situation_field_receipts(
            situation, proofs, catalog,
            pinned_raw_shas=frozenset((RAW,)),
            source_raw_market_map={RAW: "USDCHF"},
        )
