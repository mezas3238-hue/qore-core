from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2ci_three_ledger_identity as r2ci,
)


def _r2f(index: int, source: str, refs: tuple[str, ...]) -> dict[str, object]:
    return {
        "market": "AUDUSD",
        "event_generation": 2,
        "state_at_c3_close": "CONFIRMED_ENTRY_SLOT_AVAILABLE",
        "source_event_id": f"src-{index}",
        "parent_c3_opened_at": "2025-01-01T00:00:00+00:00",
        "source_opened_at": source,
        "source_reference_ids": refs,
    }


def _r2g(r2f_row: dict[str, object], *, policy: str, refs: tuple[str, ...]) -> dict[str, object]:
    return {
        "market": "AUDUSD",
        "c3_opened_at": r2f_row["parent_c3_opened_at"],
        "source_opened_at": r2f_row["source_opened_at"],
        "reference_ids": refs,
        "competition_policy": policy,
    }


def test_exact_identity_joins_c3_source_and_reference_ids() -> None:
    src = _r2f(1, "2025-01-01T01:00:00+00:00", ("b", "a"))
    row = _r2g(src, policy=r2ci.CURRENT_NEWEST, refs=("a", "b"))
    k1 = r2ci._exact("AUDUSD", str(src["parent_c3_opened_at"]), str(src["source_opened_at"]), ("b", "a"))
    k2 = r2ci._exact("AUDUSD", str(row["c3_opened_at"]), str(row["source_opened_at"]), ("a", "b"))
    assert k1 == k2
    with pytest.raises(ValueError, match="Duplicate reference"):
        r2ci._exact("AUDUSD", str(src["parent_c3_opened_at"]), str(src["source_opened_at"]), ("a", "a"))


def test_old_policy_one_attempt_and_frozen_count_gate() -> None:
    src = _r2f(1, "2025-01-01T01:00:00+00:00", ("a",))
    newest = _r2g(src, policy=r2ci.CURRENT_NEWEST, refs=("a",))
    report = {
        "identity": r2ci.R2G_IDENTITY,
        "market": "AUDUSD",
        "one_trade_attempt_max_per_parent": True,
        "policy_family": [r2ci.CURRENT_NEWEST],
        "policies": {r2ci.CURRENT_NEWEST: {"full_2y": {"trades": 1}}},
    }
    r2ci._verify_r2g("AUDUSD", (newest,), report)
    with pytest.raises(ValueError, match="one selected trade"):
        r2ci._verify_r2g("AUDUSD", (newest, newest), report)
    altered = deepcopy(report)
    altered["policies"][r2ci.CURRENT_NEWEST]["full_2y"]["trades"] = 2
    with pytest.raises(ValueError, match="trade-count drift"):
        r2ci._verify_r2g("AUDUSD", (newest,), altered)


def test_unsupported_market_and_historical_scope() -> None:
    assert r2ci.R2CH_EXPECTED == {"AUDUSD": 43, "USDJPY": 32}
    assert r2ci.R2F_RUN == 35811162435
    assert r2ci.R2G_RUN == 35811391351
