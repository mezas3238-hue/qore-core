"""Actual VT31 G3 COG source-only emission: no fabricated CognitiveDecision."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    M1Bar,
)
from scripts.vt31_m2_dol_reconciliation_20261014 import DATES
from scripts.vt31_m2_native_cog_real_m1_20261014 import (
    audit_groups,
    audit_one_day,
)


def m1(
    opened: datetime, o: str = "100", hi: str = "102",
    lo: str = "98", c: str = "100.5",
) -> M1Bar:
    return M1Bar(
        opened, opened + timedelta(minutes=1), Decimal(o),
        Decimal(hi), Decimal(lo), Decimal(c),
    )


def actual_g3_fixture(day: tuple[int, int, int]) -> tuple[M1Bar, ...]:
    """M1 OHLC synthetic, but ALL COG decisions are emitted by the real class.

    Pattern is pinned to the native COG adversarial source test #930:
    native 10:06 LONG MSS, Asia HIGH 120 formed at 03:00, no next draw touch.
    """
    start = datetime(*day, 0, tzinfo=NEW_YORK).astimezone(UTC)
    patterns = [
        ("100", "103", "99", "101"),
        ("101", "103", "100", "100.5"),
        ("101", "105", "100", "102"),
        ("101", "104", "100", "101"),
        ("101", "104", "100", "104"),
        ("101", "109", "101", "107"),
    ]
    rows = []
    for i in range(606):
        t = start + timedelta(minutes=i)
        if i == 45:
            row = m1(t, hi="120")
        elif i == 55:
            row = m1(t, lo="80")
        elif i >= 600:
            o, hi, lo, c = patterns[i - 600]
            row = m1(t, o=o, hi=hi, lo=lo, c=c)
        else:
            row = m1(t)
        rows.append(row)
    return tuple(rows)


@pytest.mark.parametrize("day", [(2025, 7, 1), (2025, 1, 15)])
def test_original_native_cog_not_synthetic_dto_agrees_with_source_witnesses(day):
    rows = actual_g3_fixture(day)
    observed = audit_one_day(datetime(*day).date().isoformat(), rows)
    assert observed["M1_closed_session_prefixes"] == 66
    assert observed["native_decisions_emitted_prefixes_not_trades"] >= 1
    real_emissions = observed["emissions"]
    assert all(r["real_native_decision"] is True for r in real_emissions)
    assert all(r["native_g3_policy"] == "QORE_G3_MSS_CLOSE_V1_PROPOSED"
               for r in real_emissions)
    last = next(r for r in real_emissions
                if r["as_of"] == rows[-1].closed_at.isoformat())
    assert last["dol_family"] == "ASIA_NY_CLOCK_HIGH"
    assert last["side"] == "LONG"
    assert last["p3_state"] == "SUPPORTED", last
    assert last["v1_state"] == "SUPPORTED", last
    assert last["first_native_thesis_not_trade"] is True
    assert last["broker_ack_or_fills"] == 0
    assert not last["method_certified"]
    assert not last["cognition_certified"]
    assert not last["execution_authorized"]


def test_future_extra_m1_cannot_change_preceding_native_decisions():
    day = (2025, 7, 1)
    source = actual_g3_fixture(day)
    baseline = audit_one_day("2025-07-01", source)
    new_bar = m1(source[-1].closed_at, hi="130")
    expanded = audit_one_day("2025-07-01", source + (new_bar,))
    assert expanded["emissions"][:len(baseline["emissions"])] == baseline["emissions"]
    assert baseline["native_decisions_emitted_prefixes_not_trades"] > 0


def test_missing_all_m1_never_creates_native_or_external_cog_confirmation():
    report = audit_groups({d: () for d in DATES})
    assert report["expected_closed_M1_session_slots"] == 2160
    assert report["observed_closed_M1_session_prefixes"] == 0
    assert report["missing_M1_session_slots"] == 2160
    assert report["scope_verdict"] == "NATIVE_COG_EMISSION_NOT_EVALUABLE"
    assert report["pair_matrix_actual_emitted_cog_only"] == {}
    assert report["native_cog_tested"] is True
    assert report["native_emission_prefixes_not_trades"] == 0
    assert report["broker_ack_or_fills"] == 0
    assert report["profit_factor"] is None
    assert not report["method_certified"]
    assert not report["trader_certified"]


def test_nonchronological_m1_rejected_before_witness():
    source = actual_g3_fixture((2025, 7, 1))
    scrambled = source[:5] + (source[4],) + source[5:]
    with pytest.raises(ValueError, match="NON_CAUSAL"):
        audit_one_day("2025-07-01", scrambled)


def test_no_fabricated_cog_when_no_swing_break():
    start = datetime(2025, 7, 1, tzinfo=NEW_YORK).astimezone(UTC)
    flat = tuple(
        m1(start + timedelta(minutes=i), o="100", hi="101",
           lo="99", c="100")
        for i in range(606)
    )
    observed = audit_one_day("2025-07-01", flat)
    assert observed["native_decisions_emitted_prefixes_not_trades"] == 0
    assert observed["emissions"] == []
    assert observed["M1_closed_session_prefixes"] == 66
