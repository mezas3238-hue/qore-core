from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_index_v3_fresh_validation import (
    HOLDOUT_END_EXCLUSIVE,
    HOLDOUT_START,
    Vt08IndexV3FreshValidationError,
    _bootstrap_path,
    validate_fresh_holdout,
)
from qore.infrastructure.trader_lab.vt08_index_v3_geometry_candidate import (
    CANDIDATE_ID,
    RULE_FINGERPRINT,
)


def _payload() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    markets = ("NAS100", "SP500", "US30")
    for index in range(36):
        rows.append(
            {
                "symbol": markets[index % 3],
                "anchor_hour_new_york": 6 if index % 2 == 0 else 10,
                "side": "long" if index % 2 == 0 else "short",
                "r_multiple": "0.6" if index % 4 != 3 else "-0.2",
            }
        )
    provenance = {
        market: {
            "account_fingerprint": "a" * 64,
            "provider_symbol": market,
            "software_sha": "b" * 40,
        }
        for market in markets
    }
    return {
        "schema": "qore.trader_lab.vt08_index_v3_geometry_candidate.v1",
        "candidate_id": CANDIDATE_ID,
        "rule_fingerprint": RULE_FINGERPRINT,
        "partition": {
            "start_date": HOLDOUT_START,
            "end_date_exclusive": HOLDOUT_END_EXCLUSIVE,
        },
        "provenance": provenance,
        "trades": rows,
    }


def test_bootstrap_is_deterministic_and_replicate_separated() -> None:
    values = (
        Decimal("1"),
        Decimal("-1"),
        Decimal("2"),
        Decimal("-0.5"),
        Decimal("0.25"),
    )
    first = _bootstrap_path(values, seed=20260914, replicate=7, block_length=3)
    again = _bootstrap_path(values, seed=20260914, replicate=7, block_length=3)
    other = _bootstrap_path(values, seed=20260914, replicate=8, block_length=3)
    assert first == again
    assert first != other


def test_strong_synthetic_holdout_passes_all_frozen_gates() -> None:
    result = validate_fresh_holdout(_payload())
    assert result["fresh_holdout_opened"] is True
    assert result["fresh_holdout_pass"] is True
    governance = result["governance"]
    assert isinstance(governance, dict)
    assert governance["demo_eligible"] is False
    assert governance["post_result_tuning_permitted"] is False


def test_side_collapse_is_rejected() -> None:
    payload = deepcopy(_payload())
    rows = payload["trades"]
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, dict)
        if row["side"] == "short":
            row["r_multiple"] = "-1"
    result = validate_fresh_holdout(payload)
    structural = result["structural"]
    assert isinstance(structural, dict)
    checks = structural["checks"]
    assert isinstance(checks, dict)
    assert checks["every_side_positive"] is False
    assert result["fresh_holdout_pass"] is False


def test_small_sample_is_rejected() -> None:
    payload = deepcopy(_payload())
    rows = payload["trades"]
    assert isinstance(rows, list)
    payload["trades"] = rows[:12]
    result = validate_fresh_holdout(payload)
    structural = result["structural"]
    assert isinstance(structural, dict)
    checks = structural["checks"]
    assert isinstance(checks, dict)
    assert checks["sample"] is False
    assert result["fresh_holdout_pass"] is False


def test_partition_drift_fails_closed() -> None:
    payload = _payload()
    payload["partition"] = {
        "start_date": "2022-09-16",
        "end_date_exclusive": HOLDOUT_END_EXCLUSIVE,
    }
    with pytest.raises(Vt08IndexV3FreshValidationError, match="partition mismatch"):
        validate_fresh_holdout(payload)
