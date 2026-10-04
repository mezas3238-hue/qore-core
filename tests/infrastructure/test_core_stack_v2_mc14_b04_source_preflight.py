from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.mc14_b04_source_preflight import (
    B04SourceDisposition,
    assess_b04_source_pack,
)


def _sensor(
    family: str,
    *,
    empty_bid: int,
    empty_ask: int,
    full_coverage: bool,
    dataset_hash: str,
) -> dict[str, object]:
    return {
        "family": family,
        "status": "source_only_complete",
        "window_count": 2948,
        "empty_bid_window_count": empty_bid,
        "empty_ask_window_count": empty_ask,
        "full_bid_ask_window_coverage": full_coverage,
        "global_dataset_sha256": dataset_hash,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
    }


def _pack() -> dict[str, object]:
    return {
        "workflow_run_id": 36765098842,
        "git_sha": "aec788d073aedc31f609c1609af3f7d4d8e5ae30",
        "source_manifest_sha256": (
            "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
        ),
        "reduced_evidence_sha256": (
            "f60309f92b9ea462d2bab0b275f9262013e6c248e877d91f3fd3e2c5f4405d82"
        ),
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "sensors": {
            "US2000_BREADTH_PROXY": _sensor(
                "US2000_BREADTH_PROXY",
                empty_bid=23,
                empty_ask=23,
                full_coverage=False,
                dataset_hash=(
                    "1984901a5dfd45bf627de48bdde72645560b07d1b35648e287330faee294d1e9"
                ),
            ),
            "XAUUSD_DEFENSIVE_PROXY": _sensor(
                "XAUUSD_DEFENSIVE_PROXY",
                empty_bid=0,
                empty_ask=0,
                full_coverage=True,
                dataset_hash=(
                    "f1ae7a1a4a59d6c7e657feddcd6534c6d371db6a48812200a6b0ec15f0dd3e65"
                ),
            ),
        },
    }


def test_b04_preflight_preserves_real_source_coverage_disposition() -> None:
    result = assess_b04_source_pack(_pack())

    assert result.ready_families == ("XAUUSD_DEFENSIVE_PROXY",)
    assert result.insufficient_families == ("US2000_BREADTH_PROXY",)
    assert (
        result.families[0].disposition
        is B04SourceDisposition.INSUFFICIENT_DO_NOT_INFER
    )
    assert (
        result.families[1].disposition
        is B04SourceDisposition.READY_FOR_SINGLE_GOVERNED_REPLAY
    )


def test_b04_preflight_fails_closed_if_target_was_read() -> None:
    payload = deepcopy(_pack())
    payload["target_or_outcome_read"] = True

    with pytest.raises(ValueError, match="research governance"):
        assess_b04_source_pack(payload)


def test_b04_preflight_rejects_lineage_drift() -> None:
    payload = deepcopy(_pack())
    payload["git_sha"] = "0" * 40

    with pytest.raises(ValueError, match="unexpected B04 acquisition SHA"):
        assess_b04_source_pack(payload)


def test_b04_preflight_rejects_window_count_drift() -> None:
    payload = deepcopy(_pack())
    payload["sensors"]["XAUUSD_DEFENSIVE_PROXY"]["window_count"] = 2947

    with pytest.raises(ValueError, match="window count drifted"):
        assess_b04_source_pack(payload)


def test_b04_preflight_is_deterministic() -> None:
    first = assess_b04_source_pack(_pack())
    second = assess_b04_source_pack(_pack())

    assert first.fingerprint() == second.fingerprint()
