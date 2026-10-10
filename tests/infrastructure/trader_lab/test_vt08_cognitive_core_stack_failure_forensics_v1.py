from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_failure_forensics_v1 import (
    AXES,
    FORENSIC_MARKETS,
)


def test_failure_forensics_scope_is_diagnostics_only_universe() -> None:
    assert FORENSIC_MARKETS == ("CADJPY", "NZDUSD")
    assert AXES == (
        "anchor",
        "side",
        "risk_ref_band",
        "c2_body_band",
        "protected_swing_age_band",
        "reference_body_alignment",
    )
