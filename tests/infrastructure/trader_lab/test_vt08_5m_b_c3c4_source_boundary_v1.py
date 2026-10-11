"""B no-lookahead C3/C4 test gate; source complete NEVER inferred from EQ."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    vt08_5m_b_c3c4_source_boundary_v1 as b,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

T0 = datetime(2026, 1, 5, 6, tzinfo=UTC)


def bar(when: datetime, op: str, high: str, low: str, close: str) -> Vt08B01Bar:
    return Vt08B01Bar(
        opened_at=when,
        closed_at=when + timedelta(minutes=15),
        open=Decimal(op),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_c3_eq_calculated_from_full_h4_range_only_after_closed_m15() -> None:
    rows = tuple(
        bar(T0 + timedelta(minutes=15 * i), "100", "103", "97", "102")
        for i in range(16)
    )
    values = b._h4(rows)
    assert values["high"] == Decimal("103")
    assert values["low"] == Decimal("97")
    assert (values["high"] + values["low"]) / 2 == Decimal("100")
    assert len(b._sha_m15(rows)) == 64
    with pytest.raises(ValueError, match="exactly 16"):
        b._h4(rows[:15])


@pytest.mark.parametrize("side", ("long", "short"))
def test_c3_opposing_series_proxy_can_only_confirm_after_closed_bar(side: str) -> None:
    if side == "long":
        rows = (
            bar(T0, "101", "102", "98", "99"),
            bar(T0 + timedelta(minutes=15), "100", "102", "96", "97"),
            bar(T0 + timedelta(minutes=30), "97", "104", "96", "103"),
        )
    else:
        rows = (
            bar(T0, "99", "102", "98", "101"),
            bar(T0 + timedelta(minutes=15), "100", "104", "98", "103"),
            bar(T0 + timedelta(minutes=30), "103", "104", "96", "97"),
        )
    ps = b._source_ps_proxy(rows, side)
    assert len(ps) == 1
    assert b._timestamp(ps[0][0]) == T0
    assert b._timestamp(ps[0][1]) == T0 + timedelta(minutes=45)
    assert T0 < b._timestamp(ps[0][1])


def test_c3_source_schema_unknown_cannot_reach_cognitive_bridge() -> None:
    with pytest.raises(ValueError, match="unrecognized"):
        b.verify_c3_shape(
            {"schema": "VT08_5M_CANDIDATE_EVENT_V1"}, {}
        )
    with pytest.raises(ValueError, match="must be at its H4 close"):
        b.verify_c3_shape({"schema":b.SCHEMA, "as_of_stage":"C4"}, {})


def test_b_rejects_unavailable_source_files_instead_of_inventing_poi(
    tmp_path: Path,
) -> None:
    with pytest.raises((ValueError, FileNotFoundError)):
        b.audit_market(tmp_path / "missing-a.json", tmp_path / "missing-raw.json")


def test_c4_missing_first_m15_cannot_be_counted_as_observed() -> None:
    parent: dict[str, object] = {
        "origin_id": "id",
        "snapshot_fingerprint": "abc",
        "closed_at": T0,
    }
    observed = {
        "schema": b.SCHEMA,
        "as_of_stage": "C4_FIRST_M15_CLOSED",
        "origin_id": "id",
        "parent_snapshot_fingerprint": "abc",
        "observed_at": (T0 + timedelta(minutes=15)).isoformat(),
    }
    with pytest.raises(ValueError, match="physical bar absent"):
        b.verify_c4_observation(observed, parent, {})


def test_c4_observation_cannot_claim_parent_which_differs() -> None:
    parent: dict[str, object] = {
        "origin_id": "id",
        "snapshot_fingerprint": "abc",
        "closed_at": T0,
    }
    observed = {
        "schema": b.SCHEMA,
        "as_of_stage": "C4_FIRST_M15_CLOSED",
        "origin_id": "some-other-id",
        "parent_snapshot_fingerprint": "abc",
    }
    with pytest.raises(ValueError, match="lineage must match"):
        b.verify_c4_observation(observed, parent, {})


def test_c4_early_snapshot_does_not_have_first_m15_close() -> None:
    parent: dict[str, object] = {
        "origin_id": "id",
        "snapshot_fingerprint": "abc",
        "closed_at": T0,
    }
    observed = {
        "schema": b.SCHEMA,
        "as_of_stage": "C4_FIRST_M15_CLOSED",
        "origin_id": "id",
        "parent_snapshot_fingerprint": "abc",
        "observed_at": T0.isoformat(),
    }
    with pytest.raises(ValueError, match="cannot be known before"):
        b.verify_c4_observation(observed, parent, {})
