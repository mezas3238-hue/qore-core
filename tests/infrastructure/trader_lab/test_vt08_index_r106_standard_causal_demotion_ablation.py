from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r106_standard_causal_demotion_ablation as r106,
)


def test_r106_identity_and_source_are_frozen() -> None:
    assert r106.IDENTITY == (
        "VT08_INDEX_R106_STANDARD_CAUSAL_DEMOTION_ABLATION_001"
    )
    assert r106.SOURCE_R105_RUN_ID == 35556744176
    assert r106.SOURCE_R105_ARTIFACT_ID == 10620118359
    assert r106.SOURCE_R105_ARTIFACT_DIGEST == (
        "sha256:6a81182ff3e710509b755cad94cb84f1901adfdb02aa706a444c7591fe1df381"
    )


def test_r106_floor_reuses_existing_qore_floor() -> None:
    assert r106.FLOOR == Decimal("0.005")


def test_r106_is_single_feature_only() -> None:
    assert all(
        policy.dimension is None or isinstance(policy.dimension, str)
        for policy in r106.POLICIES
    )
    assert len(r106.POLICIES) == 6


def test_r106_preregistered_contexts_match_r105() -> None:
    by_id = {policy.policy_id: policy for policy in r106.POLICIES}
    assert by_id[
        "STANDARD_CURRENT_SOURCE_DAY_BODY_OPPOSED"
    ].label == "opposed"
    assert by_id["STANDARD_SHORT_CISD"].label == "short|cisd"
    assert by_id[
        "STANDARD_RISK_FRACTION_030_050"
    ].label == "0.30-0.50%"
