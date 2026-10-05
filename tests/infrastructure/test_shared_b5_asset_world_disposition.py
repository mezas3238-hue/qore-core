from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.shared_b5_asset_world_disposition import (
    AgriculturalWorldDisposition,
    B5AssetWorldError,
    CommodityWorldDisposition,
    assess_agricultural_world,
    assess_commodity_world,
)


def test_b14_current_provider_truth_is_known_blindspot_not_proxy() -> None:
    receipt = assess_agricultural_world(
        authorized_provider_count=1,
        agricultural_candidate_count=0,
        soft_candidate_count=0,
        livestock_candidate_count=0,
        secondary_provider_owner_authorized=False,
        secondary_provider_scientifically_admitted=False,
        proxy_agriculture_used=False,
        evidence_refs=(
            "artifact:11059457712",
            "run:36623645085",
        ),
    )
    assert receipt.disposition is AgriculturalWorldDisposition.KNOWN_BLINDSPOT
    assert "ZERO_AGRICULTURAL_SOFT_LIVESTOCK_CANDIDATES" in receipt.blocker_codes
    assert receipt.proxy_agriculture_used is False
    assert receipt.execution_authority is False
    assert len(receipt.fingerprint()) == 64


def test_b14_forbids_proxy_and_unauthorized_scientific_admission() -> None:
    with pytest.raises(B5AssetWorldError, match="proxy fabrication"):
        assess_agricultural_world(
            authorized_provider_count=1,
            agricultural_candidate_count=0,
            soft_candidate_count=0,
            livestock_candidate_count=0,
            secondary_provider_owner_authorized=False,
            secondary_provider_scientifically_admitted=False,
            proxy_agriculture_used=True,
            evidence_refs=("sealed:b14",),
        )

    with pytest.raises(B5AssetWorldError, match="Owner authorization"):
        assess_agricultural_world(
            authorized_provider_count=1,
            agricultural_candidate_count=0,
            soft_candidate_count=0,
            livestock_candidate_count=0,
            secondary_provider_owner_authorized=False,
            secondary_provider_scientifically_admitted=True,
            proxy_agriculture_used=False,
            evidence_refs=("sealed:b14",),
        )


def test_b15_inherited_truth_remains_governed_unknown() -> None:
    receipt = assess_commodity_world(
        metal_reference_object_count=11,
        metal_provider_neutral_identity_count=0,
        energy_reference_object_count=3,
        energy_provider_neutral_identity_count=0,
        dated_gc_contract_count=5,
        expired_gc_contract_count=5,
        current_front_contract_verified_count=0,
        roll_semantics_verified=False,
        continuous_series_verified=False,
        venue_identity_verified=False,
        evidence_refs=(
            "artifact:11128416668",
            "artifact:11128739693",
            "artifact:11129012317",
        ),
    )
    assert receipt.disposition is CommodityWorldDisposition.GOVERNED_UNKNOWN
    assert "OBSERVED_GC_SET_EXPIRED" in receipt.blocker_codes
    assert "CURRENT_FRONT_CONTRACT_UNVERIFIED" in receipt.blocker_codes
    assert "ROLL_SEMANTICS_UNVERIFIED" in receipt.blocker_codes
    assert "CONTINUOUS_SERIES_UNVERIFIED" in receipt.blocker_codes
    assert receipt.inference_used is False
    assert receipt.execution_authority is False
    assert len(receipt.fingerprint()) == 64


def test_b15_forbids_front_roll_or_identity_inference() -> None:
    with pytest.raises(B5AssetWorldError, match="inference is forbidden"):
        assess_commodity_world(
            metal_reference_object_count=11,
            metal_provider_neutral_identity_count=0,
            energy_reference_object_count=3,
            energy_provider_neutral_identity_count=0,
            dated_gc_contract_count=5,
            expired_gc_contract_count=5,
            current_front_contract_verified_count=0,
            roll_semantics_verified=False,
            continuous_series_verified=False,
            venue_identity_verified=False,
            evidence_refs=("sealed:b15",),
            inference_used=True,
        )
