from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    CiboChronologicalReplayError,
    CiboChronologicalReplayTrade,
    CiboReplayCausalTrade,
    CiboReplayOutcome,
    ReplayEconomicsStatus,
    ReplayProviderEconomics,
    ReplaySignalFingerprintOrigin,
    build_replay_opportunity,
    reconstructed_signal_fingerprint,
)


NOW = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)


def _economics() -> ReplayProviderEconomics:
    return ReplayProviderEconomics(
        provider_symbol="GBPJPY",
        tick_size=Decimal("0.001"),
        tick_value=Decimal("1.25"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        margin_per_volume=Decimal("250"),
        execution_cost_reserve_per_volume_usd=Decimal("0.50"),
        broker_risk_buffer=Decimal("1.05"),
        evidence_id="provider-calibration-1",
    )


def _causal(
    *,
    economics_status: ReplayEconomicsStatus = (
        ReplayEconomicsStatus.PROVIDER_ECONOMICS_COMPLETE
    ),
    provider_economics: ReplayProviderEconomics | None = None,
    pre_trade_state: tuple[tuple[str, str], ...] = (
        ("session", "london"),
        ("regime", "stable"),
    ),
) -> CiboReplayCausalTrade:
    evidence = ("raw-m5-artifact-1", "target-ledger-artifact-2")
    fingerprint = reconstructed_signal_fingerprint(
        trader_id=TraderLineage.R38_GBPJPY,
        qore_symbol="GBPJPY",
        side="long",
        signal_at=NOW,
        entry_at=NOW + timedelta(minutes=5),
        entry_price=Decimal("201.000"),
        structural_stop=Decimal("200.800"),
        technical_target=Decimal("201.500"),
        source_evidence_ids=evidence,
    )
    if provider_economics is None and (
        economics_status is ReplayEconomicsStatus.PROVIDER_ECONOMICS_COMPLETE
    ):
        provider_economics = _economics()
    return CiboReplayCausalTrade(
        trader_id=TraderLineage.R38_GBPJPY,
        signal_fingerprint=fingerprint,
        signal_fingerprint_origin=(
            ReplaySignalFingerprintOrigin.PHASE18_RECONSTRUCTED
        ),
        qore_symbol="GBPJPY",
        side="long",
        signal_at=NOW,
        entry_at=NOW + timedelta(minutes=5),
        entry_price=Decimal("201.000"),
        structural_stop=Decimal("200.800"),
        technical_target=Decimal("201.500"),
        legacy_risk_scale=Decimal("0.25"),
        minimum_execution_steps=1,
        pre_trade_state=pre_trade_state,
        source_evidence_ids=evidence,
        economics_status=economics_status,
        provider_economics=provider_economics,
    )


def test_r_denominated_trade_is_retained_but_cannot_size_cibo() -> None:
    causal = _causal(
        economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
        provider_economics=None,
    )

    with pytest.raises(
        CiboChronologicalReplayError,
        match="provider economics calibration required",
    ):
        build_replay_opportunity(causal)


def test_complete_economics_builds_volume_free_replay_opportunity() -> None:
    causal = _causal()
    opportunity = build_replay_opportunity(causal)

    assert opportunity.trader_id is TraderLineage.R38_GBPJPY
    assert opportunity.intended_entry == Decimal("201.000")
    assert opportunity.stop_loss == Decimal("200.800")
    assert opportunity.take_profit == Decimal("201.500")
    assert opportunity.minimum_volume == Decimal("0.01")
    assert opportunity.volume_step == Decimal("0.01")
    assert opportunity.margin_per_volume == Decimal("250")

    expected = (
        (Decimal("0.200") / Decimal("0.001")) * Decimal("1.25")
        + Decimal("0.50")
    ) * Decimal("1.05")
    assert opportunity.stop_loss_per_volume == expected

    # The old Trader risk scale remains evidence only; it never enters the
    # volume-free opportunity contract.
    assert causal.legacy_risk_scale == Decimal("0.25")
    assert not hasattr(opportunity, "legacy_risk_scale")


def test_outcome_cannot_change_cibo_replay_input() -> None:
    causal = _causal()
    winner = CiboChronologicalReplayTrade(
        causal=causal,
        outcome=CiboReplayOutcome(
            exit_at=NOW + timedelta(hours=1),
            raw_outcome_r=Decimal("2.0"),
            net_outcome_r=Decimal("1.9"),
            exit_reason="TARGET",
        ),
    )
    loser = CiboChronologicalReplayTrade(
        causal=causal,
        outcome=CiboReplayOutcome(
            exit_at=NOW + timedelta(hours=1),
            raw_outcome_r=Decimal("-1"),
            net_outcome_r=Decimal("-1.1"),
            exit_reason="STOP",
        ),
    )

    # build_replay_opportunity accepts causal evidence, not the combined trade.
    assert build_replay_opportunity(winner.causal) == build_replay_opportunity(
        loser.causal
    )


def test_post_trade_fields_are_rejected_from_pre_trade_state() -> None:
    with pytest.raises(
        CiboChronologicalReplayError,
        match="post-trade field forbidden",
    ):
        _causal(pre_trade_state=(("session", "london"), ("mfe", "2.4R")))


def test_reconstructed_fingerprint_is_outcome_independent_and_deterministic() -> None:
    kwargs = {
        "trader_id": TraderLineage.R38_GBPJPY,
        "qore_symbol": "GBPJPY",
        "side": "short",
        "signal_at": NOW,
        "entry_at": NOW + timedelta(minutes=5),
        "entry_price": Decimal("201.000"),
        "structural_stop": Decimal("201.200"),
        "technical_target": Decimal("200.500"),
        "source_evidence_ids": ("raw", "target"),
    }

    assert reconstructed_signal_fingerprint(**kwargs) == (
        reconstructed_signal_fingerprint(**kwargs)
    )


def test_invalid_geometry_and_temporal_order_fail_closed() -> None:
    with pytest.raises(
        CiboChronologicalReplayError,
        match="invalid long technical geometry",
    ):
        CiboReplayCausalTrade(
            trader_id=TraderLineage.R38_GBPJPY,
            signal_fingerprint="x",
            signal_fingerprint_origin=ReplaySignalFingerprintOrigin.TRADER_NATIVE,
            qore_symbol="GBPJPY",
            side="long",
            signal_at=NOW,
            entry_at=NOW + timedelta(minutes=1),
            entry_price=Decimal("201"),
            structural_stop=Decimal("202"),
            technical_target=Decimal("203"),
            legacy_risk_scale=Decimal("1"),
            minimum_execution_steps=1,
            pre_trade_state=(),
            source_evidence_ids=("evidence",),
            economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
        )

    causal = _causal()
    with pytest.raises(
        CiboChronologicalReplayError,
        match="exit_at cannot precede entry_at",
    ):
        CiboChronologicalReplayTrade(
            causal=causal,
            outcome=CiboReplayOutcome(
                exit_at=NOW,
                raw_outcome_r=Decimal("0"),
                net_outcome_r=Decimal("-0.1"),
                exit_reason="IMPOSSIBLE",
            ),
        )
