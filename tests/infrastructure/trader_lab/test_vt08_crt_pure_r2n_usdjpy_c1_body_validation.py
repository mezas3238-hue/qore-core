from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2n_usdjpy_c1_body_validation import (
    CANDIDATE_BOUNDS,
    CANDIDATE_FAMILY,
    MAX_DD_R,
    MIN_PF,
    MIN_TRADES,
    CandidateId,
    _accept,
)


def test_r2n_candidate_family_is_frozen() -> None:
    assert CANDIDATE_FAMILY == (
        CandidateId.CONTROL,
        CandidateId.C1_BODY_025_050_PRIMARY,
        CandidateId.C1_BODY_020_050,
        CandidateId.C1_BODY_025_055,
        CandidateId.C1_BODY_020_055,
    )
    assert CANDIDATE_BOUNDS[CandidateId.C1_BODY_025_050_PRIMARY] == (
        Decimal("0.25"),
        Decimal("0.50"),
    )


def test_r2n_primary_bounds_are_half_open() -> None:
    candidate = CandidateId.C1_BODY_025_050_PRIMARY

    assert not _accept(candidate, Decimal("0.2499"))
    assert _accept(candidate, Decimal("0.25"))
    assert _accept(candidate, Decimal("0.4999"))
    assert not _accept(candidate, Decimal("0.50"))


def test_r2n_control_accepts_all_body_fractions() -> None:
    assert _accept(CandidateId.CONTROL, Decimal("0"))
    assert _accept(CandidateId.CONTROL, Decimal("1"))


def test_r2n_gate_constants_are_frozen_before_results() -> None:
    assert MIN_TRADES == 20
    assert MIN_PF == 1.05
    assert MAX_DD_R == 12.0
