from qore.infrastructure.trader_lab import (
    vt08_index_r40_nas100_short_structural_prior as r40,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r41_weighted_residual_forensics as mod,
)


def test_r41_is_forensics_only_identity() -> None:
    assert mod.IDENTITY == "VT08_INDEX_R41_WEIGHTED_RESIDUAL_FORENSICS_001"


def test_r41_references_rejected_r40_exactly() -> None:
    assert r40.IDENTITY == "VT08_INDEX_R40_NAS100_SHORT_STRUCTURAL_PRIOR_001"


def test_r41_friction_surfaces_are_frozen() -> None:
    assert str(mod.PRIMARY_STRESS) == "0.05"
    assert str(mod.SECONDARY_STRESS) == "0.10"
