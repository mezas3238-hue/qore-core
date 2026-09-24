from qore.infrastructure.trader_lab.vt08_cognitive_post_anchor_ps_shape_audit_v1 import (
    _profile_mask,
)


def test_post_anchor_profile_mask_is_diagnostic_only() -> None:
    assert _profile_mask(set()) == "NONE"
    assert _profile_mask({"M15_STANDARD"}) == "M15_STANDARD"
