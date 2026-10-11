"""Audit14 replay safeguards: original book controls and no fake BID/ASK."""

from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_a2_fourteenth_causal_first_economics_v1 as replay,
)


def test_no_source_market_data_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError,match="require one frozen"):
        replay.replay_market(tmp_path,tmp_path,tmp_path)


def test_no_nine_market_economics_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError,match="nine market economic books"):
        replay.aggregate(tmp_path)


def test_aware_source_time_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError,match="aware"):
        replay.aware("2026-04-02T12:00:00")
    assert replay.aware("2026-04-02T12:00:00+00:00").year==2026


def test_economic_output_is_not_allowed_to_claim_real_quotes() -> None:
    assert "SOURCE_ANCHORED" in replay.IDENTITY
    assert "GROSS_REPLAY" in replay.IDENTITY
