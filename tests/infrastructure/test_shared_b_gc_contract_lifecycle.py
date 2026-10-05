from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import cast

import pytest

from qore.infrastructure.core_stack_v2.shared_b_gc_contract_lifecycle import (
    SharedBGcContractLifecycleError,
    build_gc_observed_contract_lifecycle,
)


def _authority() -> dict[str, object]:
    return {
        "identity": "SHARED_B_GC_CONTRACT_LIFECYCLE_AUTHORITY_EVIDENCE_001",
        "product": {
            "canonical_product_identity": "COMEX_GOLD_FUTURES_100_TROY_OZ",
            "product_symbol": "GC",
            "venue": "COMEX",
            "contract_size_troy_oz": 100,
            "termination_rule": "THIRD_LAST_BUSINESS_DAY_OF_DELIVERY_MONTH",
        },
        "authorities": [
            {
                "authority_id": "A",
                "source_url": "https://www.cmegroup.com/a",
            },
            {
                "authority_id": "B",
                "source_url": "https://www.cmegroup.com/b",
            },
        ],
        "frozen_conclusions": {
            "gc_product_identity_verified": True,
            "gc_contract_size_verified": True,
            "gc_termination_occurs_within_delivery_month": True,
            "contract_month_before_assessment_month_is_expired": True,
            "contract_month_order_alone_proves_front_contract": False,
            "contract_month_order_alone_proves_roll_rule": False,
            "dated_contract_set_proves_continuous_series": False,
            "current_provider_front_contract_may_be_inferred": False,
        },
    }


def _pack() -> dict[str, object]:
    rows = []
    specs = (
        ("GCM25", 10052, "2025-06"),
        ("GCG26", 10134, "2026-02"),
        ("GCJ26", 10135, "2026-04"),
        ("GCM26", 10136, "2026-06"),
        ("GCQ26", 10137, "2026-08"),
    )
    for symbol, symbol_id, month in specs:
        rows.append({
            "asset_world": "METALS_FUTURES",
            "identity_kind": "DATED_FUTURES_CONTRACT_DESCRIPTOR",
            "dated_contract_identity_verified": True,
            "provider": "CTRADER_DEMO",
            "provider_symbol": symbol,
            "provider_symbol_id": symbol_id,
            "observation_identity": (
                "QORE:FUTURES_CONTRACT:"
                f"COMEX_GOLD_FUTURES_100_TROY_OZ:{month}:COMEX"
            ),
        })
    return {
        "identity": "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001",
        "known_at": "2026-09-30T18:03:32+00:00",
        "records": rows,
    }


def test_all_five_observed_gc_contracts_are_expired_by_sep_2026() -> None:
    payload = build_gc_observed_contract_lifecycle(
        commodity_pack=_pack(),
        authority_evidence=_authority(),
        assessed_at=datetime(2026, 9, 30, 21, 42, tzinfo=UTC),
    )

    assert payload["dated_gc_contract_count"] == 5
    assert payload["official_gc_product_identity_verified"] is True
    assert payload["official_gc_product_venue"] == "COMEX"
    assert payload["observed_gc_contract_venue_verified_count"] == 5
    assert payload["expired_before_assessment_month_count"] == 5
    assert payload["delivery_month_exact_expiry_unresolved_count"] == 0
    assert payload["future_contract_count"] == 0
    assert (
        payload["all_observed_gc_contracts_expired_before_assessment_month"]
        is True
    )
    assert (
        payload["current_front_contract_absent_from_observed_set"]
        is True
    )
    assert payload["observed_set_can_prove_current_gc_chain"] is False
    assert payload["current_front_contract_in_observed_set_verified_count"] == 0
    assert payload["front_contract_identity_complete"] is False
    assert payload["roll_semantics_complete"] is False
    assert payload["continuous_series_semantics_complete"] is False
    assert payload["b15_complete"] is False
    assert len(str(payload["lifecycle_fingerprint_sha256"])) == 64
    assert all(
        row["lifecycle_status"] == "EXPIRED_BEFORE_ASSESSMENT_MONTH"
        and row["official_product_identity_verified"] is True
        and row["official_product_venue"] == "COMEX"
        and row["observed_contract_venue_verified"] is True
        and row["front_contract_verified"] is False
        and row["roll_semantics_verified"] is False
        and row["continuous_series_verified"] is False
        for row in cast(list[dict[str, object]], payload["records"])
    )


def test_same_delivery_month_refuses_to_guess_exact_expiry() -> None:
    pack = deepcopy(_pack())
    rows = pack["records"]
    assert isinstance(rows, list)
    rows[-1]["provider_symbol"] = "GCU26"
    rows[-1]["observation_identity"] = (
        "QORE:FUTURES_CONTRACT:"
        "COMEX_GOLD_FUTURES_100_TROY_OZ:2026-09:COMEX"
    )

    payload = build_gc_observed_contract_lifecycle(
        commodity_pack=pack,
        authority_evidence=_authority(),
        assessed_at=datetime(2026, 9, 30, 21, 42, tzinfo=UTC),
    )

    assert payload["expired_before_assessment_month_count"] == 4
    assert payload["delivery_month_exact_expiry_unresolved_count"] == 1
    assert (
        payload["all_observed_gc_contracts_expired_before_assessment_month"]
        is False
    )
    assert (
        payload["current_front_contract_absent_from_observed_set"]
        is False
    )


def test_future_contract_does_not_prove_front_contract() -> None:
    pack = deepcopy(_pack())
    rows = pack["records"]
    assert isinstance(rows, list)
    rows[-1]["provider_symbol"] = "GCZ26"
    rows[-1]["observation_identity"] = (
        "QORE:FUTURES_CONTRACT:"
        "COMEX_GOLD_FUTURES_100_TROY_OZ:2026-12:COMEX"
    )

    payload = build_gc_observed_contract_lifecycle(
        commodity_pack=pack,
        authority_evidence=_authority(),
        assessed_at=datetime(2026, 9, 30, 21, 42, tzinfo=UTC),
    )
    assert payload["future_contract_count"] == 1
    future = cast(list[dict[str, object]], payload["records"])[-1]
    assert future["lifecycle_status"] == "FUTURE_CONTRACT_NOT_FRONT_PROOF"
    assert future["front_contract_verified"] is False
    assert payload["observed_set_can_prove_current_gc_chain"] is False


def test_authority_cannot_silently_enable_roll_inference() -> None:
    authority = deepcopy(_authority())
    conclusions = authority["frozen_conclusions"]
    assert isinstance(conclusions, dict)
    conclusions["contract_month_order_alone_proves_roll_rule"] = True

    with pytest.raises(
        SharedBGcContractLifecycleError,
        match="contract_month_order_alone_proves_roll_rule",
    ):
        build_gc_observed_contract_lifecycle(
            commodity_pack=_pack(),
            authority_evidence=authority,
            assessed_at=datetime(2026, 9, 30, 21, 42, tzinfo=UTC),
        )
