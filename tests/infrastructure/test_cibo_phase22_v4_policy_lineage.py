from qore.infrastructure.cibo_next_policy_advanced_scientific_eligibility import (
    NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY,
)
from qore.infrastructure.cibo_next_policy_code_bundle_lineage import (
    NEXT_POLICY_CODE_BUNDLE_LINEAGE,
)
from qore.infrastructure.cibo_phase22_v4_policy_lineage import (
    PHASE22_V4_POLICY_LINEAGE_FREEZE,
    VT31_FROZEN_METHODOLOGY_GIT_SHA,
)


def test_v4_policy_lineage_preserves_exact_preregistered_policy() -> None:
    freeze = PHASE22_V4_POLICY_LINEAGE_FREEZE

    assert freeze.policy_bundle_sha256 == (
        NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint()
    )
    assert freeze.advanced_scientific_eligibility_sha256 == (
        NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
    )
    assert freeze.vt31_methodology_git_sha == VT31_FROZEN_METHODOLOGY_GIT_SHA
    assert freeze.v3_lane_artifact_contents_used_for_policy_selection is False
    assert freeze.policy_retuned_after_v3 is False
    assert freeze.advanced_eligibility_changed_after_v3 is False
    assert freeze.trader_methodology_changed_after_v3 is False
    assert freeze.trader_parameters_changed_after_v3 is False
    assert freeze.selection_thresholds_changed_after_v3 is False
    assert freeze.vt31_source_abi_repair_authorized is True
    assert freeze.productive_authority is False
    assert freeze.fingerprint().startswith("sha256:")
