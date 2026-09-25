from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_index_v2_fresh_validation import (
    ANCHORS,
    CANDIDATE_ID,
    HOLDOUT_END_EXCLUSIVE,
    HOLDOUT_START,
    MARKETS,
    MONTE_CARLO_ALGORITHM,
    SELECTION_ID,
    Vt08IndexV2FreshValidationError,
    _bootstrap_path,
    validate_fresh_holdout,
)


def _candidate_report(count: int = 120) -> dict[str, object]:
    trades: list[dict[str, object]] = []
    for index in range(count):
        value = Decimal("-0.1") if index % 4 == 0 else Decimal("0.2")
        trades.append(
            {
                "symbol": MARKETS[index % len(MARKETS)],
                "anchor_hour_new_york": ANCHORS[
                    (index // len(MARKETS)) % len(ANCHORS)
                ],
                "r_multiple": str(value),
            }
        )
    fingerprint = "a" * 64
    return {
        "schema": "qore.trader_lab.vt08_index_v2_candidate.v1",
        "candidate_id": CANDIDATE_ID,
        "development_selection_id": SELECTION_ID,
        "variant": {"variant_id": SELECTION_ID},
        "partition": {
            "start_date": HOLDOUT_START,
            "end_date_exclusive": HOLDOUT_END_EXCLUSIVE,
        },
        "provenance": {
            market: {"account_fingerprint": fingerprint} for market in MARKETS
        },
        "trades": trades,
    }


def test_block_bootstrap_is_deterministic() -> None:
    values = tuple(Decimal(index) for index in range(10))
    first = _bootstrap_path(values, seed=7, replicate=3, block_length=5)
    second = _bootstrap_path(values, seed=7, replicate=3, block_length=5)
    assert first == second
    assert len(first) == len(values)


def test_block_bootstrap_domain_separates_replicates() -> None:
    values = tuple(Decimal(index) for index in range(20))
    first = _bootstrap_path(values, seed=7, replicate=3, block_length=5)
    second = _bootstrap_path(values, seed=7, replicate=4, block_length=5)
    assert first != second


def test_pre_registered_fresh_validation_accepts_robust_synthetic_series() -> None:
    result = validate_fresh_holdout(_candidate_report())
    assert result["fresh_holdout_opened"] is True
    assert result["fresh_holdout_pass"] is True
    structural = result["structural"]
    stress = result["stress"]
    monte_carlo = result["monte_carlo"]
    assert isinstance(structural, dict) and structural["pass"] is True
    assert isinstance(stress, dict) and stress["pass"] is True
    assert isinstance(monte_carlo, dict) and monte_carlo["pass"] is True
    assert monte_carlo["algorithm"] == MONTE_CARLO_ALGORITHM


def test_pre_registered_fresh_validation_rejects_too_small_sample() -> None:
    result = validate_fresh_holdout(_candidate_report(12))
    assert result["fresh_holdout_pass"] is False


def test_partition_drift_fails_closed() -> None:
    payload = _candidate_report()
    partition = payload["partition"]
    assert isinstance(partition, dict)
    partition["end_date_exclusive"] = "2024-08-14"
    with pytest.raises(Vt08IndexV2FreshValidationError):
        validate_fresh_holdout(payload)
