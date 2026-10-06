from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ceiling_discovery import CiboCeilingLimitKind
from qore.infrastructure.cibo_ceiling_discovery_assembly import (
    assemble_ceiling_discovery,
)
from qore.infrastructure.cibo_single_account_sovereign_ceiling_run import (
    CiboCeilingAblationReceipt,
    CiboSovereignCeilingDecisionReceipt,
    CiboSovereignCeilingSettlementReceipt,
    build_single_account_sovereign_ceiling_run,
)

T0 = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
SHA = "sha256:" + "a" * 64


def _decision(
    signal: str,
    *,
    risk: str,
    requested: str = "0",
    authorized: str = "0",
    requested_risk: str = "0",
    authorized_risk: str = "0",
    authorized_margin: str = "0",
    multiplier: int = 0,
) -> CiboSovereignCeilingDecisionReceipt:
    return CiboSovereignCeilingDecisionReceipt(
        decision_epoch_id="epoch-1",
        decision_id="decision-" + signal,
        option_id="option-" + signal,
        signal_fingerprint=signal,
        trader_id="R34_XAUUSD",
        decided_at=T0,
        capital_disposition=(
            "RISK_REVIEW_READY"
            if risk != "NOT_REQUESTED"
            else "COGNITIVE_BLOCK"
        ),
        risk_decision=risk,
        requested_volume=Decimal(requested),
        authorized_volume=Decimal(authorized),
        requested_stop_risk_usd=Decimal(requested_risk),
        authorized_stop_risk_usd=Decimal(authorized_risk),
        authorized_margin_usd=Decimal(authorized_margin),
        adaptive_leverage_multiplier=multiplier,
        sizing_mode="CAPABILITY_MAXIMUM",
        semantic_digest="sha256:" + "b" * 64,
        native_mpc_derived_from_cognition=True,
    )


def _ablations() -> tuple[CiboCeilingAblationReceipt, ...]:
    return tuple(
        CiboCeilingAblationReceipt(
            name=name,
            ending_capital_usd=Decimal("65"),
            maximum_drawdown_usd=Decimal("2"),
        )
        for name in (
            "sizing",
            "adaptive_leverage",
            "cibo_compound",
            "compound_portfolio",
            "cognition",
        )
    )


def test_receipt_preserves_one_usd60_account_and_risk_attribution() -> None:
    decisions = (
        _decision(
            "signal-a",
            risk="ALLOW",
            requested="0.02",
            authorized="0.02",
            requested_risk="2",
            authorized_risk="2",
            authorized_margin="4",
            multiplier=2,
        ),
        _decision("signal-b", risk="NOT_REQUESTED"),
    )
    settlements = (
        CiboSovereignCeilingSettlementReceipt(
            signal_fingerprint="signal-a",
            trader_id="R34_XAUUSD",
            settled_at=T0 + timedelta(minutes=30),
            realized_net_pnl_usd=Decimal("10"),
            settlement_sha256="sha256:" + "c" * 64,
        ),
    )

    run = build_single_account_sovereign_ceiling_run(
        source_manifest_sha256=SHA,
        decision_count=2,
        decisions=decisions,
        settlements=settlements,
        ablations=_ablations(),
        population_exhausted=False,
        growth_capacity_remaining_at_population_end=False,
        intrinsic_ceiling_claimed=True,
        observed_lower_bound_only=False,
        limiting_factor=CiboCeilingLimitKind.MARGIN,
    )

    assert run["initial_capital_usd"] == "60"
    assert run["ending_capital_usd"] == "70"
    assert run["peak_capital_usd"] == "70"
    assert run["maximum_drawdown_usd"] == "0"
    assert run["account_reset_count"] == 0
    assert run["economic_era_reset_count"] == 0
    assert run["risk_decision_counts"] == {
        "NOT_REQUESTED": 1,
        "ALLOW": 1,
        "REDUCE": 0,
        "REJECT": 0,
    }
    assert run["adaptive_leverage_distribution"]["2"] == 1
    assert run["native_mpc_derived_decision_count"] == 2


def test_receipt_composes_with_ceiling_discovery_assembler() -> None:
    decisions = (
        _decision(
            "signal-a",
            risk="ALLOW",
            requested="0.02",
            authorized="0.02",
            requested_risk="2",
            authorized_risk="2",
            authorized_margin="4",
            multiplier=2,
        ),
    )
    run = build_single_account_sovereign_ceiling_run(
        source_manifest_sha256=SHA,
        decision_count=1,
        decisions=decisions,
        settlements=(
            CiboSovereignCeilingSettlementReceipt(
                signal_fingerprint="signal-a",
                trader_id="R34_XAUUSD",
                settled_at=T0 + timedelta(minutes=30),
                realized_net_pnl_usd=Decimal("10"),
                settlement_sha256="sha256:" + "d" * 64,
            ),
        ),
        ablations=_ablations(),
        population_exhausted=False,
        growth_capacity_remaining_at_population_end=False,
        intrinsic_ceiling_claimed=True,
        observed_lower_bound_only=False,
        limiting_factor=CiboCeilingLimitKind.MARGIN,
    )
    preflight = {
        "schema": "qore.cibo.native-max-intelligence-preflight.v1",
        "source_manifest_sha256": SHA,
        "decision_count": 1,
        "native_max_pass_count": 1,
        "native_max_blocked_count": 0,
        "maximum_intelligence_ready": True,
        "external_ai_call_count": 0,
    }

    assembled = assemble_ceiling_discovery(
        native_preflight=preflight,
        sovereign_run=run,
    )

    assert assembled["classification"] == "INTRINSIC_CEILING"
    assert assembled["ceiling_discovery_ready_to_close"] is True
    assert assembled["capital_multiple"] == str(Decimal("70") / Decimal("60"))


def test_settlement_cannot_exist_without_risk_authorized_selection() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="settlement lacks Risk-authorized selection",
    ):
        build_single_account_sovereign_ceiling_run(
            source_manifest_sha256=SHA,
            decision_count=1,
            decisions=(_decision("signal-a", risk="NOT_REQUESTED"),),
            settlements=(
                CiboSovereignCeilingSettlementReceipt(
                    signal_fingerprint="signal-a",
                    trader_id="R34_XAUUSD",
                    settled_at=T0 + timedelta(minutes=30),
                    realized_net_pnl_usd=Decimal("1"),
                    settlement_sha256="sha256:" + "e" * 64,
                ),
            ),
            ablations=_ablations(),
            population_exhausted=True,
            growth_capacity_remaining_at_population_end=True,
            intrinsic_ceiling_claimed=False,
            observed_lower_bound_only=True,
            limiting_factor=(
                CiboCeilingLimitKind.OPPORTUNITY_POPULATION_EXHAUSTED
            ),
        )


def test_receipt_requires_exact_five_causal_ablations() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="exact mandatory ablation set",
    ):
        build_single_account_sovereign_ceiling_run(
            source_manifest_sha256=SHA,
            decision_count=1,
            decisions=(_decision("signal-a", risk="NOT_REQUESTED"),),
            settlements=(),
            ablations=_ablations()[:-1],
            population_exhausted=True,
            growth_capacity_remaining_at_population_end=True,
            intrinsic_ceiling_claimed=False,
            observed_lower_bound_only=True,
            limiting_factor=(
                CiboCeilingLimitKind.OPPORTUNITY_POPULATION_EXHAUSTED
            ),
        )


def test_risk_reduce_must_reduce_requested_volume() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="Risk REDUCE must lower requested volume",
    ):
        _decision(
            "signal-a",
            risk="REDUCE",
            requested="0.02",
            authorized="0.02",
            requested_risk="2",
            authorized_risk="2",
            authorized_margin="4",
            multiplier=2,
        )
