"""R6 UNKNOWN retrospective forensics are NEVER causal trade decisions."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_gm4_unknown_root_forensics import (
    BEYOND,
    MISSING,
    diagnose_gm4_unknowns_expost,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

MARKET = CrtPureMarket.AUDUSD
START = datetime(2025, 1, 1, tzinfo=UTC)
H4 = timedelta(hours=4)
M5 = timedelta(minutes=5)
C3 = START + 3 * H4
DECISION = C3 + timedelta(minutes=45)


def source() -> dict:
    return {
        "source_event_id": "case-a",
        "market": "AUDUSD",
        "c3_H4_opened_at_utc": C3.isoformat(),
        "decision_clock_utc": DECISION.isoformat(),
        "parent_direction": "BULLISH",
        "structural_invalidation_price_if_candidate": "90",
    }


def record(outcome: str) -> dict:
    return {
        "source_event_id": "case-a", "market": "AUDUSD",
        "source_decision_clock_utc": DECISION.isoformat(),
        "parent_c3_utc": C3.isoformat(),
        "not_a_trade": True, "no_PnL_or_sizing": True,
        "G_M4_PASS": False,
        "terminal_observation_proven": False,
        "terminal_observed_at_utc": None,
        "price_path_outcome_only_post_decision": outcome,
    }


def raw_m5(*, missing: datetime | None = None, entry_open: int = 100):
    bars = []
    for block in range(4):
        for i in range(48):
            stamp = START + block * H4 + i * M5
            if stamp == missing:
                continue
            price = entry_open if stamp == DECISION else 100
            bars.append(ReplayBar(
                opened_at=stamp,
                open_price=price,
                high_price=max(price, 110 if block == 1 and i == 0 else 100),
                low_price=min(price, 95 if block == 1 and i == 0 else 100),
                close_price=100,
            ))
    return tuple(bars)


def examine(outcome: str, bars):
    return diagnose_gm4_unknowns_expost(
        MARKET, bars, (source(),), (record(outcome),)
    )


def test_entry_already_beyond_c1_destination_is_not_claimed_as_terminal() -> None:
    summary, rows = examine(BEYOND, raw_m5(entry_open=103))
    assert summary["unknown_cases"] == 1
    assert rows[0]["observed_issue"] == "ALREADY_BEYOND_DESTINATION"
    assert rows[0]["gm4_terminal_remains_UNKNOWN"]
    assert rows[0]["forensics_is_expost_only"]
    assert rows[0]["G_M4_PASS"] is False
    assert rows[0]["no_capital_authority"] is True


def test_first_missing_m5_is_reported_without_fake_price_hit() -> None:
    missing = DECISION + 2 * M5
    summary, rows = examine(MISSING, raw_m5(missing=missing))
    assert summary["unknown_cases"] == 1
    assert rows[0]["observed_issue"] == "SOURCE_M5_GAP"
    assert rows[0]["first_missing_original_m5_opened_at_utc"] == missing.isoformat()
    assert rows[0]["previous_m5_present"]
    assert rows[0]["next_original_m5_opened_at_within_C3_utc"] == (
        missing + M5
    ).isoformat()
    assert rows[0]["gm4_terminal_remains_UNKNOWN"]


def test_entry_without_beyond_barrier_geometry_rejected() -> None:
    with pytest.raises(ValueError, match="not reproduced"):
        examine(BEYOND, raw_m5(entry_open=100))


def test_missing_which_is_not_missing_rejected() -> None:
    with pytest.raises(ValueError, match="not reproduced"):
        examine(MISSING, raw_m5())


@pytest.mark.parametrize("attack", ["faked_pass", "market", "fake_terminal"])
def test_gm4_attestation_forgeries_denied(attack: str) -> None:
    g = record(BEYOND)
    if attack == "faked_pass":
        g["G_M4_PASS"] = True
    elif attack == "market":
        g["market"] = "USDJPY"
    else:
        g["terminal_observed_at_utc"] = (DECISION + M5).isoformat()
    with pytest.raises(ValueError):
        diagnose_gm4_unknowns_expost(
            MARKET, raw_m5(entry_open=103), (source(),), (g,)
        )


def test_forensics_requires_original_gm4_source_identity() -> None:
    case = source()
    case["source_event_id"] = "forged"
    with pytest.raises(ValueError, match="source identities"):
        diagnose_gm4_unknowns_expost(
            MARKET, raw_m5(entry_open=103), (case,), (record(BEYOND),)
        )
