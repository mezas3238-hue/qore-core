from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    CiboChronologicalReplayError,
    CiboChronologicalReplayTrade,
    CiboReplayCapitalSample,
    CiboReplayCausalTrade,
    CiboReplayOutcome,
    ReplayEconomicsStatus,
    ReplayProviderEconomics,
    ReplaySignalFingerprintOrigin,
    build_replay_opportunity,
    score_cibo_capital_path,
    score_legacy_replay,
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
    first = reconstructed_signal_fingerprint(
        trader_id=TraderLineage.R38_GBPJPY,
        qore_symbol="GBPJPY",
        side="short",
        signal_at=NOW,
        entry_at=NOW + timedelta(minutes=5),
        entry_price=Decimal("201.000"),
        structural_stop=Decimal("201.200"),
        technical_target=Decimal("200.500"),
        source_evidence_ids=("raw", "target"),
    )
    second = reconstructed_signal_fingerprint(
        trader_id=TraderLineage.R38_GBPJPY,
        qore_symbol="GBPJPY",
        side="short",
        signal_at=NOW,
        entry_at=NOW + timedelta(minutes=5),
        entry_price=Decimal("201.000"),
        structural_stop=Decimal("201.200"),
        technical_target=Decimal("200.500"),
        source_evidence_ids=("raw", "target"),
    )

    assert first == second


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


def test_legacy_replay_scoring_preserves_chronology_and_risk_scale() -> None:
    base = _causal()
    trades = (
        CiboChronologicalReplayTrade(
            causal=replace(
                base,
                signal_fingerprint="trade-a",
                entry_at=NOW + timedelta(minutes=5),
                legacy_risk_scale=Decimal("0.25"),
            ),
            outcome=CiboReplayOutcome(
                exit_at=NOW + timedelta(minutes=30),
                raw_outcome_r=Decimal("2"),
                net_outcome_r=Decimal("2"),
                exit_reason="TARGET",
            ),
        ),
        CiboChronologicalReplayTrade(
            causal=replace(
                base,
                signal_fingerprint="trade-b",
                entry_at=NOW + timedelta(minutes=60),
                legacy_risk_scale=Decimal("0.50"),
            ),
            outcome=CiboReplayOutcome(
                exit_at=NOW + timedelta(minutes=90),
                raw_outcome_r=Decimal("-1"),
                net_outcome_r=Decimal("-1"),
                exit_reason="STOP",
            ),
        ),
        CiboChronologicalReplayTrade(
            causal=replace(
                base,
                signal_fingerprint="trade-c",
                entry_at=NOW + timedelta(minutes=120),
                legacy_risk_scale=Decimal("0.50"),
            ),
            outcome=CiboReplayOutcome(
                exit_at=NOW + timedelta(minutes=150),
                raw_outcome_r=Decimal("-1"),
                net_outcome_r=Decimal("-1"),
                exit_reason="STOP_PROTECTED_SWING",
            ),
        ),
    )

    metrics = score_legacy_replay(trades)

    assert metrics.trades == 3
    assert metrics.gross_profit_r == Decimal("0.50")
    assert metrics.gross_loss_r == Decimal("-1.00")
    assert metrics.total_r == Decimal("-0.50")
    assert metrics.profit_factor == Decimal("0.5")
    assert metrics.max_drawdown_r == Decimal("1.00")
    assert metrics.max_loss_streak == 2
    assert metrics.stop_count == 2


def test_legacy_replay_rejects_duplicate_signal_identity() -> None:
    causal = _causal()
    trade = CiboChronologicalReplayTrade(
        causal=causal,
        outcome=CiboReplayOutcome(
            exit_at=NOW + timedelta(hours=1),
            raw_outcome_r=Decimal("1"),
            net_outcome_r=Decimal("1"),
            exit_reason="TARGET",
        ),
    )

    with pytest.raises(
        CiboChronologicalReplayError,
        match="duplicate replay signal fingerprint",
    ):
        score_legacy_replay((trade, trade))


def _capital_sample(
    *,
    at: datetime,
    base_risk: str,
    margin: str,
    risk_headroom: str,
    margin_headroom: str,
    self_financing: str,
    future_capacity: str,
    released: str,
    evidence_id: str,
    reconciled: bool = True,
) -> CiboReplayCapitalSample:
    return CiboReplayCapitalSample(
        observed_at=at,
        original_base_capital_at_risk_usd=Decimal(base_risk),
        margin_in_use_usd=Decimal(margin),
        hard_risk_headroom_usd=Decimal(risk_headroom),
        margin_headroom_usd=Decimal(margin_headroom),
        self_financing_capacity_usd=Decimal(self_financing),
        available_future_capacity_usd=Decimal(future_capacity),
        cumulative_released_capacity_usd=Decimal(released),
        evidence_id=evidence_id,
        reconciled=reconciled,
    )


def test_capital_path_scores_recovery_block_time_and_optionality() -> None:
    entry_at = NOW + timedelta(minutes=5)
    exit_at = NOW + timedelta(minutes=95)
    samples = (
        _capital_sample(
            at=entry_at,
            base_risk="10",
            margin="100",
            risk_headroom="90",
            margin_headroom="900",
            self_financing="0",
            future_capacity="90",
            released="0",
            evidence_id="entry",
        ),
        _capital_sample(
            at=NOW + timedelta(minutes=35),
            base_risk="5",
            margin="80",
            risk_headroom="95",
            margin_headroom="920",
            self_financing="4",
            future_capacity="95",
            released="5",
            evidence_id="protect",
        ),
        _capital_sample(
            at=NOW + timedelta(minutes=65),
            base_risk="0",
            margin="50",
            risk_headroom="100",
            margin_headroom="950",
            self_financing="10",
            future_capacity="100",
            released="10",
            evidence_id="recovered",
        ),
        _capital_sample(
            at=exit_at,
            base_risk="0",
            margin="0",
            risk_headroom="100",
            margin_headroom="1000",
            self_financing="0",
            future_capacity="110",
            released="15",
            evidence_id="exit",
        ),
    )

    metrics = score_cibo_capital_path(
        entry_at=entry_at,
        exit_at=exit_at,
        samples=samples,
    )

    assert metrics.samples == 4
    assert metrics.peak_original_capital_at_risk_usd == Decimal("10")
    assert metrics.peak_margin_in_use_usd == Decimal("100")
    assert metrics.peak_self_financing_capacity_usd == Decimal("10")
    assert metrics.ending_available_future_capacity_usd == Decimal("110")
    assert metrics.cumulative_released_capacity_usd == Decimal("15")
    assert metrics.peak_risk_utilization == Decimal("0.1")
    assert metrics.peak_margin_utilization == Decimal("0.1")
    assert metrics.base_recovery_seconds == Decimal("3600.0")
    assert metrics.base_recovered_before_exit is True
    assert metrics.base_capital_block_seconds == Decimal("3600.0")
    assert metrics.false_recovery_incidents == 0


def test_capital_path_surfaces_false_recovery_and_fails_on_bad_evidence() -> None:
    entry_at = NOW + timedelta(minutes=5)
    exit_at = NOW + timedelta(minutes=65)
    recovered_at = NOW + timedelta(minutes=25)
    reexposed_at = NOW + timedelta(minutes=45)

    samples = (
        _capital_sample(
            at=entry_at,
            base_risk="10",
            margin="10",
            risk_headroom="90",
            margin_headroom="90",
            self_financing="0",
            future_capacity="90",
            released="0",
            evidence_id="entry",
        ),
        _capital_sample(
            at=recovered_at,
            base_risk="0",
            margin="5",
            risk_headroom="100",
            margin_headroom="95",
            self_financing="5",
            future_capacity="100",
            released="10",
            evidence_id="recovered",
        ),
        _capital_sample(
            at=reexposed_at,
            base_risk="2",
            margin="5",
            risk_headroom="98",
            margin_headroom="95",
            self_financing="3",
            future_capacity="98",
            released="10",
            evidence_id="reexposed",
        ),
        _capital_sample(
            at=exit_at,
            base_risk="0",
            margin="0",
            risk_headroom="100",
            margin_headroom="100",
            self_financing="0",
            future_capacity="100",
            released="12",
            evidence_id="exit",
        ),
    )

    metrics = score_cibo_capital_path(
        entry_at=entry_at,
        exit_at=exit_at,
        samples=samples,
    )
    assert metrics.false_recovery_incidents == 1

    unreconciled = replace(samples[-1], reconciled=False)
    with pytest.raises(
        CiboChronologicalReplayError,
        match="unreconciled capital sample",
    ):
        score_cibo_capital_path(
            entry_at=entry_at,
            exit_at=exit_at,
            samples=(*samples[:-1], unreconciled),
        )

    decreasing_release = replace(
        samples[-1],
        cumulative_released_capacity_usd=Decimal("9"),
    )
    with pytest.raises(
        CiboChronologicalReplayError,
        match="cumulative released capacity cannot decrease",
    ):
        score_cibo_capital_path(
            entry_at=entry_at,
            exit_at=exit_at,
            samples=(*samples[:-1], decreasing_release),
        )
