from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_readiness import (
    assess_phase20_t12_oos_readiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_oos_utility import (
    assess_phase20_t12_oos_utility,
)


def _empty_readiness():
    return assess_phase20_t12_oos_readiness(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        treatment_policy_book=VersionedPhase20ForwardPolicyBook(generation=0),
        shadow_decisions=(),
    )


def test_t12_utility_fails_closed_before_population_is_ready() -> None:
    report = assess_phase20_t12_oos_utility(
        qualification_rows=(),
        readiness=_empty_readiness(),
        shadow_decisions=(),
    )

    assert report.population_ready is False
    assert report.fresh_oos_utility_demonstrated is False
    assert report.runtime_authority is False
    assert report.outcome_refit_performed is False
    assert report.treatment_net_delta_usd == Decimal("0")
    assert report.control_net_delta_usd == Decimal("0")
    assert "T12_MINIMUM_DECISION_EPOCHS_NOT_MET" in report.blockers


def test_t12_utility_requires_canonical_qualification_rows() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="canonical qualification rows",
    ):
        assess_phase20_t12_oos_utility(
            qualification_rows=(object(),),  # type: ignore[arg-type]
            readiness=_empty_readiness(),
            shadow_decisions=(),
        )


def test_t12_utility_requires_canonical_shadow_tuple() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="canonical shadow decisions",
    ):
        assess_phase20_t12_oos_utility(
            qualification_rows=(),
            readiness=_empty_readiness(),
            shadow_decisions=(object(),),  # type: ignore[arg-type]
        )
