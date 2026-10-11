"""Original winner source identity must not be inferred from aggregated PnL."""

from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_a2_fourteenth_winner_reconciliation_v1 as audit,
)


def test_reference_book_missing_fails_closed(tmp_path:Path)->None:
    with pytest.raises(ValueError,match="2876 IDs"):
        audit.reconcile(tmp_path)


def test_trade_keys_cannot_omit_market_day_or_family()->None:
    row={
        "symbol":"AUDJPY","session":"ASIA","operating_date":"2026-01-05",
        "v49_entry_at":"2026-01-05T01:10:00+00:00",
        "source_family":"LIQUIDITY_SWEEP_CISD",
        "online_entry_at":"2026-01-05T01:05:00+00:00",
        "online_family":"FVG_RETRACE_CISD",
    }
    assert len(audit.source_key(row))==5
    assert audit.source_key(row)!=audit.candidate_key(row)
    assert audit.IDENTITY.endswith("WINNER_IDENTITY_CHECK_V1")
