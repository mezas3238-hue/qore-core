from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_arch2_t11_gross_edge_oos import (
    T11GrossEdgeFreshObservation,
    evaluate_t11_gross_edge_fresh_oos,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    FROZEN_AT,
    REQUIRED_SYMBOLS,
)

_LINEAGES = (
    TraderLineage.R38_GBPJPY,
    TraderLineage.R43_GBPUSD,
    TraderLineage.R42_AUDJPY,
    TraderLineage.R38_EURUSD,
    TraderLineage.R34_XAUUSD,
    TraderLineage.VT08_FOREX,
    TraderLineage.VT31_NAS100,
)
_SYMBOLS = (
    "GBPJPY",
    "GBPUSD",
    "AUDJPY",
    "EURUSD",
    "XAUUSD",
    "EURUSD",
    "NAS100",
)


def _population() -> tuple[T11GrossEdgeFreshObservation, ...]:
    rows: list[T11GrossEdgeFreshObservation] = []
    minute = 1
    for repeat in range(10):
        for trader, symbol in zip(_LINEAGES, _SYMBOLS, strict=True):
            # Set the fresh outcome equal to the immutable frozen prediction.
            from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
                frozen_train_prior_for,
            )

            outcome = frozen_train_prior_for(trader).expected_structural_r
            rows.append(
                T11GrossEdgeFreshObservation(
                    evidence_id=f"{trader.value}-{repeat}",
                    signal_fingerprint=f"sig-{trader.value}-{repeat}",
                    trader_id=trader,
                    qore_symbol=symbol,
                    observed_at=FROZEN_AT + timedelta(minutes=minute),
                    structural_outcome_r=outcome,
                    stop_risk_per_volume_usd=Decimal("10"),
                    outcome_reconciled=True,
                    provider_bound=True,
                    fresh_oos_source_authorized=True,
                )
            )
            minute += 1
    return tuple(rows)


def test_gross_edge_validates_frozen_prior_without_refit() -> None:
    result = evaluate_t11_gross_edge_fresh_oos(_population())

    assert result.observation_count == 70
    assert len(result.represented_lineages) == 7
    assert result.minimum_outcomes_per_lineage == 10
    assert tuple(item.qore_symbol for item in result.symbols) == REQUIRED_SYMBOLS
    assert result.four_of_four_nonworse is True
    assert result.fresh_oos_validated is True
    assert result.temporal_stability_validated is True
    assert result.model_refit_performed is False
    assert result.productive_authority is False
    assert result.fingerprint().startswith("sha256:")
