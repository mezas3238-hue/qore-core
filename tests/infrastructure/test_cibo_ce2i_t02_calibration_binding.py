from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedToolDisposition,
    evaluate_structural_leverage,
)
from qore.infrastructure.cibo_ce2i_t02_calibration_binding import (
    T02_BURNED_CONTEXT_RULES,
    T02_CALIBRATOR_GIT_SHA,
    T02_CONTEXT_ARTIFACT_DIGEST,
    T02_CONTEXT_ARTIFACT_ID,
    T02_CONTEXT_CALIBRATION_SHA256,
    build_t02_structural_leverage_evidence,
)
from qore.infrastructure.r34_xauusd_live import (
    R34LiveSignal,
    build_r34_opportunity,
)
from qore.infrastructure.r38_eurusd_live import (
    R38Dol,
    R38LiveSignal,
    build_r38_opportunity,
)

_NOW = datetime(2026, 9, 28, 16, 30, tzinfo=UTC)


def _provider(symbol: str, *, bid: str, ask: str) -> SimpleNamespace:
    return SimpleNamespace(
        provider_symbol=symbol,
        bid=Decimal(bid),
        ask=Decimal(ask),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.00001"),
        tick_value=Decimal("1"),
        margin_per_volume=Decimal("1000"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        open_commission_per_lot_usd=Decimal("7"),
    )


def _opportunity(
    lineage: TraderLineage,
    *,
    side: str = "long",
    context: tuple[tuple[str, str], ...] = (),
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=lineage,
        signal_fingerprint=f"{lineage.value}-signal",
        qore_symbol="TEST",
        provider_symbol="TEST",
        side=side,
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("90") if side == "long" else Decimal("110"),
        take_profit=Decimal("120") if side == "long" else Decimal("80"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("25"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("1"),
        decision_context=context,
    )


def test_t02_binding_metadata_is_frozen_to_sealed_github_artifact() -> None:
    assert T02_CONTEXT_ARTIFACT_ID == 10983002685
    assert T02_CONTEXT_ARTIFACT_DIGEST == (
        "sha256:168c48e011ef3be8acaa2d69540279bcd4126e6f5d8002c80e4708c2741813d8"
    )
    assert T02_CONTEXT_CALIBRATION_SHA256 == (
        "495810a3333537a4d7c159d4112e71b379de77096bda100fb838f3c539e11cb3"
    )
    assert T02_CALIBRATOR_GIT_SHA == "16ef0327f84423c9449e7d59679b7bd864880e8c"
    assert len(T02_BURNED_CONTEXT_RULES) == 7
    assert sum(
        row.eligible_for_structural_leverage for row in T02_BURNED_CONTEXT_RULES
    ) == 4


def test_r34_live_builder_preserves_family_needed_by_frozen_t02_rule() -> None:
    signal = R34LiveSignal(
        signal_fingerprint="a" * 64,
        entry_at=_NOW,
        timeframe="H1",
        side="long",
        certified_entry=Decimal("4300.00"),
        stop_loss=Decimal("4297.20"),
        take_profit=Decimal("4320.00"),
        target_rank=1,
        target_route="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
        decision_source="R30_CORE",
        family="LONG_DELAYED_RECLAIM_MEDIUM_BODY",
        risk_scale=Decimal("1"),
    )
    provider = _provider("XAUUSD", bid="4299.90", ask="4300.00")
    provider.contract_size = Decimal("100")
    provider.tick_size = Decimal("0.01")
    opportunity = build_r34_opportunity(signal=signal, provider_spec=provider)

    assert opportunity.context_value("family") == "LONG_DELAYED_RECLAIM_MEDIUM_BODY"
    evidence = build_t02_structural_leverage_evidence(
        opportunity=opportunity,
        observed_at=_NOW,
        released_risk_capacity_usd=Decimal("2"),
    )
    assert evidence is not None
    assert evidence.sample_size == 35


def test_r38_eurusd_context_binds_but_runtime_minimum_remains_strict() -> None:
    signal = R38LiveSignal(
        signal_fingerprint="b" * 64,
        entry_at=_NOW,
        timeframe="H1",
        side="long",
        certified_entry=Decimal("1.10000"),
        stop_loss=Decimal("1.09950"),
        take_profit=Decimal("1.10400"),
        target_rank=1,
        target_route="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
        decision_source="R30_CORE",
        family=None,
        posture="STATIC",
        fragility_flags=("BALANCED_M5_VOLATILITY",),
        base_fragility_scale=Decimal("0.50"),
        structural_overlay_scale=Decimal("1"),
        risk_scale=Decimal("0.50"),
        ladder=(
            R38Dol(1, "1.10400", "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1"),
        ),
    )
    opportunity = build_r38_opportunity(
        signal=signal,
        provider_spec=_provider("EURUSD", bid="1.09998", ask="1.10000"),
    )

    assert opportunity.context_value("target_route") == (
        "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1"
    )
    evidence = build_t02_structural_leverage_evidence(
        opportunity=opportunity,
        observed_at=_NOW,
        released_risk_capacity_usd=Decimal("2"),
    )
    assert evidence is not None
    assert evidence.sample_size == 27
    decision = evaluate_structural_leverage(
        opportunity=opportunity,
        evidence=evidence,
        current_volume=Decimal("0.01"),
        maximum_additional_volume=Decimal("0.20"),
    )
    assert decision.disposition is AdvancedToolDisposition.FAIL_CLOSED


def test_side_only_t02_context_uses_core_side_without_duplicate_metadata() -> None:
    opportunity = _opportunity(TraderLineage.R43_GBPUSD, side="long")
    evidence = build_t02_structural_leverage_evidence(
        opportunity=opportunity,
        observed_at=_NOW,
    )

    assert opportunity.context_value("side") == "long"
    assert evidence is not None
    assert evidence.sample_size == 186


def test_mismatch_and_empirically_ineligible_lineages_produce_no_evidence() -> None:
    mismatch = _opportunity(
        TraderLineage.R34_XAUUSD,
        context=(("family", "OTHER_FAMILY"),),
    )
    ineligible = _opportunity(
        TraderLineage.R42_AUDJPY,
        context=(("fragility_flag_count", "2"),),
    )

    assert build_t02_structural_leverage_evidence(
        opportunity=mismatch,
        observed_at=_NOW,
    ) is None
    assert build_t02_structural_leverage_evidence(
        opportunity=ineligible,
        observed_at=_NOW,
    ) is None
