from __future__ import annotations

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_v3_execution_authorization import (
    AUTHORIZATION_ID,
    SOVEREIGN_BRANCH,
    build_phase22_v3_execution_authorization,
)


def test_v3_authorization_binds_exact_frozen_inputs_and_is_one_shot() -> None:
    auth = build_phase22_v3_execution_authorization(
        owner_authorization_id="OWNER_PHASE22_V3_TEST",
        authorized_parent_head_sha="a" * 40,
    )

    assert auth.authorization_id == AUTHORIZATION_ID
    assert auth.target_branch == SOVEREIGN_BRANCH
    assert auth.candidate_id == (
        "CIBO_USD60_6M_HOLDOUT_2015-04-19_2015-10-19_V3"
    )
    assert auth.source_receipt_sha256.startswith("sha256:")
    assert auth.policy_bundle_sha256.startswith("sha256:")
    assert auth.advanced_scientific_eligibility_sha256.startswith("sha256:")
    assert auth.fresh_holdout_execution_authorized is True
    assert auth.one_shot_only is True
    assert auth.second_execution_authorized is False
    assert auth.broker_mutation_authorized is False
    assert auth.live_authorized is False
    assert auth.real_capital_authorized is False
    assert auth.production_authorized is False
    assert auth.merge_authorized is False
    assert auth.productive_authority is False


def test_v3_authorization_requires_explicit_owner_identity() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="explicit Owner authorization",
    ):
        build_phase22_v3_execution_authorization(
            owner_authorization_id="",
            authorized_parent_head_sha="a" * 40,
        )
