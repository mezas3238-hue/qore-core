# ruff: noqa: I001
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
    OpportunityAllocationBudget,
    allocate_competing_opportunities,
)


def _candidate(
    fingerprint: str,
    trader: TraderLineage,
    *,
    net: str,
    risk: str = "5",
    margin: str = "10",
    minutes: str = "10",
    group: str = "USD",
    concentration: str = "5",
    optionality: str = "0",
) -> CapitalOpportunityCandidate:
    return CapitalOpportunityCandidate(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        qore_symbol=fingerprint.upper(),
        provider_symbol=fingerprint.upper(),
        expected_net_value_usd=Decimal(net),
        stop_risk_usd=Decimal(risk),
        margin_usd=Decimal(margin),
        expected_capital_minutes=Decimal(minutes),
        concentration_group=group,
        concentration_risk_usd=Decimal(concentration),
        optionality_cost_usd=Decimal(optionality),
    )


def _budget(
    *,
    risk: str = "10",
    margin: str = "100",
    usd_limit: str = "100",
) -> OpportunityAllocationBudget:
    return OpportunityAllocationBudget(
        stop_risk_headroom_usd=Decimal(risk),
        margin_headroom_usd=Decimal(margin),
        concentration_limit_by_group=(("USD", Decimal(usd_limit)),),
    )


def test_higher_net_value_per_risk_minute_competes_first() -> None:
    decision = allocate_competing_opportunities(
        (
            _candidate(
                "slow",
                TraderLineage.R38_EURUSD,
                net="10",
                minutes="20",
            ),
            _candidate(
                "fast",
                TraderLineage.R43_GBPUSD,
                net="8",
                minutes="5",
            ),
        ),
        _budget(risk="5"),
    )

    assert decision.selected_signal_fingerprints == ("fast",)
    assert decision.rows[0].signal_fingerprint == "fast"
    assert decision.rows[1].reason == "shared stop-risk headroom exhausted"


def test_trader_identity_does_not_change_score_or_priority() -> None:
    left = _candidate(
        "a",
        TraderLineage.R38_EURUSD,
        net="10",
    )
    right = _candidate(
        "b",
        TraderLineage.VT31_NAS100,
        net="10",
    )

    assert left.net_value_per_risk_minute == right.net_value_per_risk_minute
    assert left.net_value_per_risk_usd == right.net_value_per_risk_usd

    decision = allocate_competing_opportunities(
        (right, left),
        _budget(risk="5"),
    )
    assert decision.selected_signal_fingerprints == ("a",)


def test_negative_adjusted_value_is_never_allocated() -> None:
    decision = allocate_competing_opportunities(
        (
            _candidate(
                "bad",
                TraderLineage.R38_EURUSD,
                net="3",
                optionality="4",
            ),
        ),
        _budget(),
    )

    assert decision.selected_signal_fingerprints == ()
    assert decision.rows[0].reason == "non-positive adjusted expected net value"


def test_margin_can_be_binding_even_when_risk_is_available() -> None:
    decision = allocate_competing_opportunities(
        (
            _candidate(
                "a",
                TraderLineage.R38_EURUSD,
                net="10",
                margin="8",
            ),
            _candidate(
                "b",
                TraderLineage.R43_GBPUSD,
                net="9",
                margin="8",
            ),
        ),
        _budget(risk="20", margin="10"),
    )

    assert decision.selected_signal_fingerprints == ("a",)
    assert decision.rows[1].reason == "shared margin headroom exhausted"


def test_concentration_limit_blocks_second_correlated_use() -> None:
    decision = allocate_competing_opportunities(
        (
            _candidate(
                "a",
                TraderLineage.R38_EURUSD,
                net="10",
                concentration="5",
            ),
            _candidate(
                "b",
                TraderLineage.R43_GBPUSD,
                net="9",
                concentration="5",
            ),
        ),
        _budget(risk="20", usd_limit="7"),
    )

    assert decision.selected_signal_fingerprints == ("a",)
    assert "concentration" in decision.rows[1].reason


def test_multiple_noncompeting_groups_can_use_shared_capital() -> None:
    decision = allocate_competing_opportunities(
        (
            _candidate(
                "eur",
                TraderLineage.R38_EURUSD,
                net="10",
                group="EUR",
            ),
            _candidate(
                "nas",
                TraderLineage.VT31_NAS100,
                net="9",
                group="INDEX",
            ),
        ),
        OpportunityAllocationBudget(
            stop_risk_headroom_usd=Decimal("20"),
            margin_headroom_usd=Decimal("100"),
            concentration_limit_by_group=(
                ("EUR", Decimal("5")),
                ("INDEX", Decimal("5")),
            ),
        ),
    )

    assert decision.selected_signal_fingerprints == ("eur", "nas")
    assert decision.used_stop_risk_usd == Decimal("10")


def test_duplicate_signal_is_rejected() -> None:
    candidate = _candidate(
        "dup",
        TraderLineage.R38_EURUSD,
        net="10",
    )

    with pytest.raises(CiboCapitalManagementError, match="duplicate"):
        allocate_competing_opportunities(
            (candidate, candidate),
            _budget(),
        )
