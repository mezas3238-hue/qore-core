"""B acceptance tests: FVG/PS prefix independently from source rules, not A code."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    vt08_5m_b_independent_three_family_receipt_audit_v1 as b,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

T0 = datetime(2026, 1, 5, 6, tzinfo=UTC)


def bar(i: int, op: str, high: str, low: str, close: str) -> Vt08B01Bar:
    t = T0 + timedelta(minutes=15 * i)
    return Vt08B01Bar(
        opened_at=t, closed_at=t + timedelta(minutes=15),
        open=Decimal(op), high=Decimal(high), low=Decimal(low),
        close=Decimal(close),
    )


def parent_fvg() -> tuple[Vt08B01Bar, ...]:
    first = [
        bar(0, "100", "101", "98", "99"),
        bar(1, "99", "103", "98", "102"),
        bar(2, "104", "106", "104", "105"),
    ]
    return tuple(first + [
        bar(i, "106", "106", "105", "105.5") for i in range(3, 16)
    ])


def test_independent_fvg_uses_third_m15_close_and_original_bounds() -> None:
    fvg = b._fvg_candidates(parent_fvg(), side="long")
    assert fvg == ((T0 + timedelta(minutes=45), Decimal("101"), Decimal("104")),)
    assert fvg[0][0] != parent_fvg()[0].closed_at


def test_fvg_missing_parent_or_invalidated_before_decision_never_survives() -> None:
    with pytest.raises(b.BSourceReceiptError, match="exact parent"):
        b._fvg_candidates(parent_fvg()[:-1], side="long")
    bars = list(parent_fvg())
    bars[8] = bar(8, "100", "106", "99", "101")
    assert b._fvg_candidates(tuple(bars), side="long") == ()


def test_opposing_series_must_be_swept_then_close_across_first_open() -> None:
    rows = (
        bar(0, "102", "103", "101", "101.5"),
        bar(1, "101.5", "102", "100", "101"),
        bar(2, "101", "104", "100", "103"),
    )
    ps = b._m15_ps(rows, side="long", important=Decimal("101"))
    assert ps == ((T0, T0 + timedelta(minutes=45), Decimal("100"), Decimal("102")),)
    assert not b._m15_ps(rows[:2], side="long", important=Decimal("101"))


def test_ps_must_break_actual_opposing_series_open_not_first_extreme() -> None:
    rows = (
        bar(0, "102", "103", "101", "101.5"),
        bar(1, "101.5", "102", "100", "101"),
        bar(2, "101", "102", "100", "101.5"),
    )
    assert not b._m15_ps(rows, side="long", important=Decimal("101"))


@pytest.mark.parametrize("payload", [
    {"market": "EURJPY", "family": "C4"},
    {"market": "EURJPY", "family": b.C2, "status": "SOURCE_COMPLETE"},
    {"market": "EURJPY", "family": b.C2,
     "status": "CONFIRMED_STRUCTURE_ONLY", "source_status": "SOURCE_COMPLETE"},
])
def test_authority_or_unknown_family_never_reaches_cognitive_gate(
    payload: dict[str, object],
) -> None:
    with pytest.raises(b.BSourceReceiptError):
        b.verify_receipt(payload, "EURJPY", {})


def test_missing_original_artifacts_are_error_not_a_source_approval(tmp_path: Path) -> None:
    with pytest.raises((FileNotFoundError, ValueError)):
        b.audit_market(tmp_path / "a-missing.json", tmp_path / "raw-missing.json")


def test_independent_source_identity_canonical_digest_changes_with_family() -> None:
    src = {"market":"EURJPY","family":b.C2,"side":"long",
           "c1_at":T0.isoformat(),"c2_at":(T0+timedelta(hours=4)).isoformat()}
    fingerprint = b._canonical_digest(src)
    assert len(fingerprint) == 64
    assert fingerprint != b._canonical_digest({**src,"family":b.C3})
