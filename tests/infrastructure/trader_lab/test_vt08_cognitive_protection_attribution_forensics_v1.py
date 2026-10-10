from qore.infrastructure.trader_lab.vt08_cognitive_protection_attribution_forensics_v1 import (
    AXES,
    FORENSIC_MARKETS,
)


def test_protection_attribution_scope_is_frozen() -> None:
    assert FORENSIC_MARKETS == ("CADJPY", "NZDUSD")
    assert AXES == (
        "anchor",
        "side",
        "risk_ref_band",
        "c2_body_band",
        "protected_swing_age_band",
        "reference_body_alignment",
    )
