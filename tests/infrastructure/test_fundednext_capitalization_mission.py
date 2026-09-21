from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import qore.infrastructure.fundednext_capitalization_mission as mission

_T0 = datetime(2026, 9, 20, 18, 0, tzinfo=UTC)
_ACCOUNT = "a" * 64


def _config(
    *,
    purchase_price: str = "149.99",
    split: str = "0.70",
) -> mission.CapitalizationMissionConfig:
    return mission.build_5k_mission_config(
        account_identity_fingerprint=_ACCOUNT,
        start_balance=Decimal("2000"),
        purchase_cash_required=Decimal(purchase_price),
        reward_split_fraction=Decimal(split),
    )


def test_current_economics_resolve_exact_5k_mission_targets() -> None:
    config = _config()

    assert config.gross_reward_required == Decimal("214.28")
    assert config.post_withdrawal_reserve == Decimal("60.00")
    assert config.minimum_trading_profit_target == Decimal("274.28")
    assert config.bank_balance_threshold == Decimal("2214.28")
    assert config.mission_balance_target == Decimal("2274.28")


def test_mission_starts_capitalizing_and_does_not_create_authority() -> None:
    snapshot = mission.evaluate_capitalization_mission(
        config=_config(),
        closed_balance=Decimal("2000"),
        equity=Decimal("2000"),
        now=_T0,
        previous=None,
        defend=False,
        payout_eligible=False,
    )

    assert snapshot.state is mission.CapitalizationMissionState.CAPITALIZE
    assert snapshot.realized_profit == 0
    assert snapshot.target_remaining == Decimal("274.28")
    assert snapshot.new_risk_allowed_by_mission is True


def test_bank_latches_once_gross_purchase_reward_is_funded() -> None:
    config = _config()
    banked = mission.evaluate_capitalization_mission(
        config=config,
        closed_balance=Decimal("2214.28"),
        equity=Decimal("2214.28"),
        now=_T0,
        previous=None,
        defend=False,
        payout_eligible=False,
    )
    slipped = mission.evaluate_capitalization_mission(
        config=config,
        closed_balance=Decimal("2200"),
        equity=Decimal("2200"),
        now=_T0,
        previous=banked,
        defend=False,
        payout_eligible=False,
    )

    assert banked.state is mission.CapitalizationMissionState.BANK
    assert slipped.state is mission.CapitalizationMissionState.BANK
    assert slipped.bank_latched is True


def test_target_reached_blocks_new_risk_without_forcing_payout_ready() -> None:
    snapshot = mission.evaluate_capitalization_mission(
        config=_config(),
        closed_balance=Decimal("2274.28"),
        equity=Decimal("2274.28"),
        now=_T0,
        previous=None,
        defend=False,
        payout_eligible=False,
    )

    assert snapshot.state is mission.CapitalizationMissionState.TARGET_REACHED
    assert snapshot.target_remaining == 0
    assert snapshot.new_risk_allowed_by_mission is False


def test_payout_ready_requires_separate_provider_eligibility() -> None:
    config = _config()
    target = mission.evaluate_capitalization_mission(
        config=config,
        closed_balance=Decimal("2274.28"),
        equity=Decimal("2274.28"),
        now=_T0,
        previous=None,
        defend=False,
        payout_eligible=False,
    )
    ready = mission.evaluate_capitalization_mission(
        config=config,
        closed_balance=Decimal("2274.28"),
        equity=Decimal("2274.28"),
        now=_T0,
        previous=target,
        defend=False,
        payout_eligible=True,
    )

    assert ready.state is mission.CapitalizationMissionState.PAYOUT_READY
    assert ready.new_risk_allowed_by_mission is False


def test_defend_overlays_active_mission_without_cancelling_target() -> None:
    snapshot = mission.evaluate_capitalization_mission(
        config=_config(),
        closed_balance=Decimal("2050"),
        equity=Decimal("1900"),
        now=_T0,
        previous=None,
        defend=True,
        payout_eligible=False,
    )

    assert snapshot.state is mission.CapitalizationMissionState.DEFEND
    assert snapshot.target_remaining == Decimal("224.28")


def test_certified_price_change_recalculates_target_instead_of_reusing_old_latch() -> None:
    old = _config(purchase_price="100.00")
    prior = mission.evaluate_capitalization_mission(
        config=old,
        closed_balance=Decimal("2205"),
        equity=Decimal("2205"),
        now=_T0,
        previous=None,
        defend=False,
        payout_eligible=False,
    )
    assert prior.target_reached_latched is True

    repriced = mission.evaluate_capitalization_mission(
        config=_config(purchase_price="149.99"),
        closed_balance=Decimal("2205"),
        equity=Decimal("2205"),
        now=_T0,
        previous=prior,
        defend=False,
        payout_eligible=False,
    )

    assert repriced.config_fingerprint != prior.config_fingerprint
    assert repriced.target_reached_latched is False
    assert repriced.state is mission.CapitalizationMissionState.CAPITALIZE


def test_durable_store_round_trips_mission_state(tmp_path) -> None:
    config = _config()
    snapshot = mission.evaluate_capitalization_mission(
        config=config,
        closed_balance=Decimal("2214.28"),
        equity=Decimal("2215"),
        now=_T0,
        previous=None,
        defend=False,
        payout_eligible=False,
    )
    store = mission.DurableCapitalizationMissionStore(
        tmp_path / "capitalization-mission.json"
    )

    store.store(snapshot)

    assert store.load() == snapshot
