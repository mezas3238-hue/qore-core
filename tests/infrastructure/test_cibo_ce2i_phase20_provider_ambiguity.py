from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    CiboReplayCausalTrade,
    ReplayEconomicsStatus,
    ReplaySignalFingerprintOrigin,
)
from qore.infrastructure.cibo_ce2i_phase20_provider_ambiguity import (
    Phase20AmbiguityEvidenceClass,
    Phase20DecimalInterval,
    Phase20PartialIdentificationStatus,
    Phase20ProviderAmbiguitySet,
    partially_identify_phase20_minimum_seed,
)


def _causal() -> CiboReplayCausalTrade:
    return CiboReplayCausalTrade(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="phase20-a-b",
        signal_fingerprint_origin=(
            ReplaySignalFingerprintOrigin.PHASE18_RECONSTRUCTED
        ),
        qore_symbol="EURUSD",
        side="long",
        signal_at=datetime(2021, 10, 1, 12, 0, tzinfo=UTC),
        entry_at=datetime(2021, 10, 1, 12, 1, tzinfo=UTC),
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        legacy_risk_scale=Decimal("1"),
        minimum_execution_steps=1,
        pre_trade_state=(),
        source_evidence_ids=("phase18:synthetic-contract",),
        economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
    )


def _interval(lower: str, upper: str) -> Phase20DecimalInterval:
    return Phase20DecimalInterval(
        lower=Decimal(lower),
        upper=Decimal(upper),
    )


def _ambiguity(
    *,
    ambiguity_id: str = "synthetic",
    liquidity_lower: str = "1",
    liquidity_upper: str = "2",
) -> Phase20ProviderAmbiguitySet:
    return Phase20ProviderAmbiguitySet(
        ambiguity_id=ambiguity_id,
        evidence_id="synthetic-contract-fixture",
        evidence_class=(
            Phase20AmbiguityEvidenceClass.EXPLICIT_COUNTERFACTUAL_BOUND
        ),
        provider_key="synthetic-provider",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        tick_size=_interval("0.1", "0.1"),
        tick_value=_interval("1", "1.2"),
        spread_ticks=_interval("1", "3"),
        commission_per_volume_usd=_interval("1", "2"),
        slippage_reserve_per_volume_usd=_interval("0", "2"),
        margin_per_volume_usd=_interval("10", "20"),
        minimum_volume=_interval("0.01", "0.02"),
        maximum_volume=_interval("10", "20"),
        volume_step=_interval("0.01", "0.02"),
        available_liquidity_volume=_interval(
            liquidity_lower,
            liquidity_upper,
        ),
        execution_delay_ms=_interval("50", "500"),
    )


def test_ambiguity_set_forbids_historical_and_outcome_tuned_claims() -> None:
    with pytest.raises(CiboCapitalManagementError, match="governance drift"):
        Phase20ProviderAmbiguitySet(
            ambiguity_id="bad",
            evidence_id="bad",
            evidence_class=(
                Phase20AmbiguityEvidenceClass.EXPLICIT_COUNTERFACTUAL_BOUND
            ),
            provider_key="p",
            qore_symbol="EURUSD",
            provider_symbol="EURUSD",
            tick_size=_interval("0.1", "0.1"),
            tick_value=_interval("1", "1"),
            spread_ticks=_interval("1", "1"),
            commission_per_volume_usd=_interval("0", "0"),
            slippage_reserve_per_volume_usd=_interval("0", "0"),
            margin_per_volume_usd=_interval("1", "1"),
            minimum_volume=_interval("0.01", "0.01"),
            maximum_volume=_interval("1", "1"),
            volume_step=_interval("0.01", "0.01"),
            available_liquidity_volume=_interval("1", "1"),
            execution_delay_ms=_interval("0", "0"),
            policy_pass_tuned=True,
        )


def test_partial_identification_can_prove_robust_feasibility() -> None:
    result = partially_identify_phase20_minimum_seed(
        causal=_causal(),
        ambiguity=_ambiguity(ambiguity_id="feasible"),
        hard_risk_headroom_usd=Decimal("10"),
        margin_headroom_usd=Decimal("10"),
    )

    assert result.status is Phase20PartialIdentificationStatus.ROBUSTLY_FEASIBLE
    assert result.historical_exact_claimed is False
    assert result.allocation_authority is False
    assert result.risk_authority is False
    assert result.execution_authority is False


def test_partial_identification_can_prove_robust_infeasibility() -> None:
    result = partially_identify_phase20_minimum_seed(
        causal=_causal(),
        ambiguity=_ambiguity(ambiguity_id="infeasible"),
        hard_risk_headroom_usd=Decimal("0.01"),
        margin_headroom_usd=Decimal("10"),
    )

    assert result.status is (
        Phase20PartialIdentificationStatus.ROBUSTLY_INFEASIBLE
    )


def test_partial_identification_preserves_uncertainty_when_bounds_cross_headroom(
) -> None:
    result = partially_identify_phase20_minimum_seed(
        causal=_causal(),
        ambiguity=_ambiguity(ambiguity_id="partial"),
        hard_risk_headroom_usd=Decimal("0.45"),
        margin_headroom_usd=Decimal("10"),
    )

    assert result.status is (
        Phase20PartialIdentificationStatus.PARTIALLY_IDENTIFIED
    )
    assert result.minimum_stop_risk_usd_lower < Decimal("0.45")
    assert result.minimum_stop_risk_usd_upper > Decimal("0.45")


def test_liquidity_bounds_participate_in_partial_identification() -> None:
    result = partially_identify_phase20_minimum_seed(
        causal=_causal(),
        ambiguity=_ambiguity(
            ambiguity_id="liquidity-partial",
            liquidity_lower="0.01",
            liquidity_upper="1",
        ),
        hard_risk_headroom_usd=Decimal("10"),
        margin_headroom_usd=Decimal("10"),
    )

    assert result.status is (
        Phase20PartialIdentificationStatus.PARTIALLY_IDENTIFIED
    )


def test_symbol_mismatch_fails_closed() -> None:
    ambiguity = _ambiguity()
    bad = Phase20ProviderAmbiguitySet(
        ambiguity_id=ambiguity.ambiguity_id,
        evidence_id=ambiguity.evidence_id,
        evidence_class=ambiguity.evidence_class,
        provider_key=ambiguity.provider_key,
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        tick_size=ambiguity.tick_size,
        tick_value=ambiguity.tick_value,
        spread_ticks=ambiguity.spread_ticks,
        commission_per_volume_usd=ambiguity.commission_per_volume_usd,
        slippage_reserve_per_volume_usd=(
            ambiguity.slippage_reserve_per_volume_usd
        ),
        margin_per_volume_usd=ambiguity.margin_per_volume_usd,
        minimum_volume=ambiguity.minimum_volume,
        maximum_volume=ambiguity.maximum_volume,
        volume_step=ambiguity.volume_step,
        available_liquidity_volume=ambiguity.available_liquidity_volume,
        execution_delay_ms=ambiguity.execution_delay_ms,
    )

    with pytest.raises(CiboCapitalManagementError, match="QORE symbol mismatch"):
        partially_identify_phase20_minimum_seed(
            causal=_causal(),
            ambiguity=bad,
            hard_risk_headroom_usd=Decimal("10"),
            margin_headroom_usd=Decimal("10"),
        )
