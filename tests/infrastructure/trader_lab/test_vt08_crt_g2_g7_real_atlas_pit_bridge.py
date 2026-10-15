"""Fixture tests for PIT provenance bridge; green synthetic tests are NOT Atlas proof."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_g2_g7_real_atlas_pit_bridge import (
    audit_v3_g2_g7_ledgers,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

MARKET = CrtPureMarket.AUDUSD
EPOCH = datetime(2025, 1, 1, tzinfo=UTC)
H4 = timedelta(hours=4)
M5 = timedelta(minutes=5)


def make_bars(
    *,
    mutate_c3: bool = False,
    missing_c0: bool = False,
    second_parent: bool = False,
) -> tuple[ReplayBar, ...]:
    # Test H4 C0/C1/C2 deliberately exhibit opposite eligible references.
    # Case 1: C2 sweeps below C1 but above C0; C0 is bearish, C1 bullish.
    profiles = {
        0: (102, 85, 100),
        1: (110, 95, 100),
        2: (105, 90, 100),
    }
    if second_parent:
        profiles.update({
            6: (102, 85, 100), 7: (110, 95, 100),
            8: (105, 90, 100),
        })
    result = []
    for block in range(10 if second_parent else 4):
        if missing_c0 and block == 0:
            continue
        high, low, close = profiles.get(block, (100, 100, 100))
        if mutate_c3 and block == 3:
            high = 250
        for i in range(48):
            result.append(ReplayBar(
                opened_at=EPOCH + block * H4 + i * M5,
                open_price=100,
                high_price=high if i == 0 else 100,
                low_price=low if i == 0 else 100,
                close_price=close if i == 47 else 100,
            ))
    return tuple(result)


def source(block: int, identity: str) -> dict:
    c3 = EPOCH + block * H4
    return {
        "market": MARKET.value,
        "source_event_id": identity,
        "conceptual_state": "CONCEPTUAL_CANDIDATE_V3",
        "source_authority_adjudicated": False,
        "independent_method_review_complete": False,
        "not_a_trade": True,
        "no_sizing_or_capital_authority": True,
        "c3_H4_opened_at_utc": c3.isoformat(),
        "decision_clock_utc": (c3 + timedelta(minutes=45)).isoformat(),
        "parent_direction": "BULLISH",
    }


def gm4(block: int, identity: str, terminal: str | None) -> dict:
    c3 = EPOCH + block * H4
    return {
        "source_event_id": identity,
        "market": MARKET.value,
        "source_decision_clock_utc": (c3 + timedelta(minutes=45)).isoformat(),
        "parent_c3_utc": c3.isoformat(),
        "initial_cognitive_action": "ABSTAIN",
        "gm5_router_blocked_at_decision": True,
        "terminal_observation_proven": terminal is not None,
        "terminal_observed_at_utc": terminal,
        "not_a_trade": True, "no_PnL_or_sizing": True,
        "G_M4_PASS": False,
    }


def bridge(
    *,
    bars=None,
    sources=None,
    paths=None,
):
    return audit_v3_g2_g7_ledgers(
        MARKET,
        make_bars() if bars is None else bars,
        (source(3, "e1"),) if sources is None else sources,
        (gm4(3, "e1", None),) if paths is None else paths,
    )


def test_real_closed_bars_detect_opposed_c0_c1_without_selecting_winner() -> None:
    summary, rows = bridge()
    row = rows[0]
    assert summary["V3_cases"] == 1
    assert row["reference_C0_complete"]
    assert row["reference_C0_rival_opposes_C1"]
    assert row["bounded_references_observed"] == 2
    assert len(set(row["reference_evidence_sha256"])) == 2
    assert row["G2_verdict"] == "WAIT"
    assert not row["G2_complete_inventory_proven"]
    assert row["G7_verdict"] == "PROVISIONAL"
    assert row["not_a_trade"] and row["no_sizing"]
    assert not summary["G_M1_PASS"] and not summary["GLOBAL_CERTIFIED"]


def test_future_c3_price_mutation_does_not_affect_g2_causal_sha() -> None:
    _, original = bridge()
    _, mutated = bridge(bars=make_bars(mutate_c3=True))
    assert original[0]["reference_evidence_sha256"] == (
        mutated[0]["reference_evidence_sha256"]
    )
    assert original[0]["G2_verdict"] == mutated[0]["G2_verdict"]


def test_incomplete_c0_does_not_invent_no_conflicts() -> None:
    summary, rows = bridge(bars=make_bars(missing_c0=True))
    assert rows[0]["reference_C0_complete"] is False
    assert rows[0]["bounded_references_observed"] == 1
    assert rows[0]["G2_verdict"] == "WAIT"
    assert summary["counts"]["C0_MISSING"] == 1


def test_unknown_terminal_stays_censored_in_later_decision() -> None:
    rows_source = (source(3, "e1"), source(9, "e2"))
    rows_gm4 = (gm4(3, "e1", None), gm4(9, "e2", None))
    summary, rows = bridge(
        bars=make_bars(second_parent=True),
        sources=rows_source, paths=rows_gm4,
    )
    assert summary["counts"]["GM4_UNKNOWN"] == 2
    assert rows[1]["G7_verdict"] == "WAIT"
    assert rows[1]["G7_prior_terminals_causally_known"] == 0
    assert rows[1]["G7_prior_terminals_censored"] == 1


def test_verified_terminal_allows_only_provisional_next_parent() -> None:
    rows_source = (source(3, "e1"), source(9, "e2"))
    close = (EPOCH + 3 * H4 + timedelta(hours=1)).isoformat()
    _, rows = bridge(
        bars=make_bars(second_parent=True),
        sources=rows_source,
        paths=(gm4(3, "e1", close), gm4(9, "e2", None)),
    )
    assert rows[1]["G7_verdict"] == "PROVISIONAL"
    assert rows[1]["G7_prior_terminals_causally_known"] == 1


def test_terminal_known_only_after_second_decision_is_censored_not_peeked() -> None:
    first = source(3, "e1")
    second = source(9, "e2")
    after_second = (EPOCH + 9 * H4 + timedelta(hours=1)).isoformat()
    _, rows = bridge(
        bars=make_bars(second_parent=True),
        sources=(first, second),
        paths=(gm4(3, "e1", after_second), gm4(9, "e2", None)),
    )
    assert rows[1]["G7_verdict"] == "WAIT"
    assert rows[1]["G7_prior_terminals_censored"] == 1


def test_gm4_future_self_terminal_does_not_affect_first_decision() -> None:
    early = (EPOCH + 3 * H4 + timedelta(hours=1)).isoformat()
    later = (EPOCH + 3 * H4 + timedelta(hours=2)).isoformat()
    _, r1 = bridge(paths=(gm4(3, "e1", early),))
    _, r2 = bridge(paths=(gm4(3, "e1", later),))
    assert r1 == r2


@pytest.mark.parametrize("attack", [
    "wrong_market", "changed_clock", "faked_pass", "missing_terminal",
    "wrong_event", "future_M5", "wrong_direction", "sizing",
])
def test_forged_or_incomplete_gm4_source_is_denied(attack: str) -> None:
    s = source(3, "e1")
    p = gm4(3, "e1", None)
    bars = make_bars()
    if attack == "wrong_market":
        p["market"] = "USDJPY"
    elif attack == "changed_clock":
        p["source_decision_clock_utc"] = EPOCH.isoformat()
    elif attack == "faked_pass":
        p["G_M4_PASS"] = True
    elif attack == "missing_terminal":
        p["terminal_observation_proven"] = True
    elif attack == "wrong_event":
        p["source_event_id"] = "forged"
    elif attack == "future_M5":
        bars = bars + (ReplayBar(
            opened_at=bars[0].opened_at, open_price=100,
            high_price=100, low_price=100, close_price=100,
        ),)
    elif attack == "wrong_direction":
        s["parent_direction"] = "BEARISH"
    else:
        s["no_sizing_or_capital_authority"] = False
    with pytest.raises(ValueError):
        bridge(bars=bars, sources=(s,), paths=(p,))



def test_g2_blind_case_contains_only_closed_h4_and_no_outcome() -> None:
    _, rows = bridge()
    packet = rows[0]["G2_blind_predecision_case"]
    assert packet is not None
    assert packet["conflict_kind"] == "OPPOSITE"
    assert packet["selected_reference"] is None
    assert not packet["independent_reviewer_adjudicated"]
    assert packet["c2_closed_at_utc"] < packet["decision_clock_utc"]
    assert all(k in packet for k in (
        "c0_closed_h4", "c1_closed_h4", "c2_closed_h4",
    ))
    assert not any(k in packet for k in (
        "outcome", "terminal", "pnl", "sizing", "future_c3",
    ))
    assert packet["not_a_trade"]


def test_g7_missing_proven_prior_is_reported_causally_and_expost_separately() -> None:
    summary, rows = bridge(
        bars=make_bars(second_parent=True),
        sources=(source(3, "e1"), source(9, "e2")),
        paths=(gm4(3, "e1", None), gm4(9, "e2", None)),
    )
    assert rows[1]["G7_verdict"] == "WAIT"
    assert rows[1]["G7_first_causally_unresolved_source_event_id"] == "e1"
    assert rows[1]["G7_prior_terminals_censored"] == 1
    assert "EX_POST" not in str(rows)
    posthoc = summary["G7_EX_POST_DIAGNOSTIC_NEVER_INITIAL_DECISION"]
    assert posthoc["WAIT_WITH_AT_LEAST_ONE_GM4_UNKNOWN"] == 1
    assert posthoc["MISSING_PRIOR_EXPOST_GM4_UNKNOWN"] == 1
    assert posthoc["first_GM4_unknown_source_event_id"] == "e1"
    assert posthoc["may_not_authorize_rearm"]


def test_g7_eventually_known_but_late_is_only_expost_analytical_label() -> None:
    later = (EPOCH + 9 * H4 + timedelta(hours=1)).isoformat()
    summary, rows = bridge(
        bars=make_bars(second_parent=True),
        sources=(source(3, "e1"), source(9, "e2")),
        paths=(gm4(3, "e1", later), gm4(9, "e2", None)),
    )
    assert rows[1]["G7_verdict"] == "WAIT"
    assert rows[1]["G7_first_causally_unresolved_source_event_id"] == "e1"
    posthoc = summary["G7_EX_POST_DIAGNOSTIC_NEVER_INITIAL_DECISION"]
    assert posthoc["WAIT_ONLY_EVENTUALLY_KNOWN_TERMINAL_LATE"] == 1
    assert posthoc["MISSING_PRIOR_EXPOST_TERMINAL_LATE"] == 1
    assert not posthoc.get("WAIT_WITH_AT_LEAST_ONE_GM4_UNKNOWN", 0)
    assert "eventually" not in str(rows).lower()


def test_g2_predecision_pack_unaffected_by_c3_price_or_gm4_terminal() -> None:
    early = (EPOCH + 3 * H4 + timedelta(hours=1)).isoformat()
    baseline = bridge()[1][0]["G2_blind_predecision_case"]
    mutated = bridge(
        bars=make_bars(mutate_c3=True),
        paths=(gm4(3, "e1", early),),
    )[1][0]["G2_blind_predecision_case"]
    assert baseline == mutated

def test_second_parent_isolated_by_market_and_prefix() -> None:
    with pytest.raises(ValueError, match="BTCUSD frozen"):
        audit_v3_g2_g7_ledgers(
            CrtPureMarket.BTCUSD, make_bars(), (), (),
        )
