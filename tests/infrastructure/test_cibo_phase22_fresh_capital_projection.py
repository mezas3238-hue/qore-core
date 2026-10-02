from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_phase22_fresh_capital_projection import (
    project_phase22_fresh_capital_input,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunity,
)
from qore.infrastructure.cibo_phase22_provider_numeric_execution import (
    Phase22ProviderNumericExecutionSpec,
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode()).hexdigest()


def _fresh(
    *,
    trader_id: TraderLineage = TraderLineage.R43_GBPUSD,
    symbol: str = "GBPUSD",
) -> Phase22FreshOpportunity:
    signal = datetime(2015, 11, 2, 10, tzinfo=UTC)
    return Phase22FreshOpportunity(
        trader_id=trader_id,
        qore_symbol=symbol,
        signal_fingerprint=_sha("signal"),
        signal_at=signal,
        entry_at=signal + timedelta(minutes=5),
        exit_at=signal + timedelta(hours=2),
        side="long",
        entry_price=Decimal("1.32000"),
        structural_stop=Decimal("1.31800"),
        technical_target=Decimal("1.32400"),
        exit_reason="target",
        gross_structural_outcome_r=Decimal("2"),
        methodology_sha256=_sha("method"),
        source_evidence_ids=(_sha("source"),),
    )


def _spec(
    *,
    symbol: str = "GBPUSD",
    provider_symbol: str = "GBPUSD",
) -> Phase22ProviderNumericExecutionSpec:
    return Phase22ProviderNumericExecutionSpec(
        qore_symbol=symbol,
        provider_symbol=provider_symbol,
        observed_at=datetime(2026, 10, 1, 20, tzinfo=UTC),
        bid=Decimal("1.32515"),
        ask=Decimal("1.32517"),
        display_digits=5,
        contract_size_per_volume=Decimal("100000"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        margin_per_volume_usd=Decimal("1325"),
        commission_per_volume_usd=Decimal("3"),
        worst_adverse_slippage_bps=Decimal("1"),
        quote_to_usd=Decimal("1"),
        usd_value_per_price_unit_per_volume=Decimal("100000"),
        derived_price_quantum=Decimal("0.00001"),
        derived_value_per_quantum_usd=Decimal("1"),
        source_provider_terms_artifact_sha256=_sha("terms"),
        source_empirical_execution_artifact_sha256=_sha("empirical"),
    )


def test_projection_separates_structural_risk_from_provider_cost() -> None:
    projection = project_phase22_fresh_capital_input(
        fresh=_fresh(),
        spec=_spec(),
        provider_numeric_freeze_sha256=_sha("freeze"),
    )

    capital = projection.candidate.capital_input
    provider = projection.provider_envelope
    assert capital.opportunity.stop_loss_per_volume == Decimal("200")
    assert capital.minimum_stop_risk_usd == Decimal("2")
    assert capital.minimum_margin_usd == Decimal("13.25")
    assert provider.commission_per_volume_usd == Decimal("3")
    assert provider.slippage_reserve_per_volume_usd == Decimal("13.20000")
    assert projection.decision_provider_cost_proxy_usd > Decimal(0)


def test_future_outcome_changes_cannot_change_predecision_projection() -> None:
    fresh = _fresh()
    mutated = replace(
        fresh,
        exit_at=fresh.exit_at + timedelta(days=1),
        exit_reason="stop",
        gross_structural_outcome_r=Decimal("-1"),
    )

    first = project_phase22_fresh_capital_input(
        fresh=fresh,
        spec=_spec(),
        provider_numeric_freeze_sha256=_sha("freeze"),
    )
    second = project_phase22_fresh_capital_input(
        fresh=mutated,
        spec=_spec(),
        provider_numeric_freeze_sha256=_sha("freeze"),
    )

    assert first == second


def test_vt31_projection_keeps_trader_volume_free_and_uses_one_provider_seed_step() -> None:
    fresh = _fresh(
        trader_id=TraderLineage.VT31_NAS100,
        symbol="NAS100",
    )
    fresh = replace(
        fresh,
        entry_price=Decimal("30000"),
        structural_stop=Decimal("29900"),
        technical_target=Decimal("30200"),
    )
    spec = _spec(symbol="NAS100", provider_symbol="USTEC")
    spec = replace(
        spec,
        bid=Decimal("30597.7"),
        ask=Decimal("30598.7"),
        display_digits=2,
        contract_size_per_volume=Decimal("1"),
        minimum_volume=Decimal("0.1"),
        volume_step=Decimal("0.1"),
        margin_per_volume_usd=Decimal("300"),
        commission_per_volume_usd=Decimal("0"),
        quote_to_usd=Decimal("1"),
        usd_value_per_price_unit_per_volume=Decimal("1"),
        derived_price_quantum=Decimal("0.01"),
        derived_value_per_quantum_usd=Decimal("0.01"),
    )

    projection = project_phase22_fresh_capital_input(
        fresh=fresh,
        spec=spec,
        provider_numeric_freeze_sha256=_sha("freeze"),
    )

    capital = projection.candidate.capital_input
    assert capital.opportunity.minimum_execution_steps == 1
    assert capital.minimum_stop_risk_usd == Decimal("10")
    assert capital.minimum_margin_usd == Decimal("30")
    assert capital.opportunity.context_value("sizing_authority") == "CIBO_CMA"
    assert capital.opportunity.context_value("trader_sizing_authority") == "NONE"
