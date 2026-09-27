from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    FROZEN_TRAIN_PRIORS,
    build_frozen_train_expectation,
    frozen_train_prior_for,
    prior_digest_sha256,
)


def test_train_prior_covers_exact_seven_traders_and_523_rows() -> None:
    assert len(FROZEN_TRAIN_PRIORS) == 7
    assert sum(item.train_rows for item in FROZEN_TRAIN_PRIORS) == 523
    assert {item.trader_id for item in FROZEN_TRAIN_PRIORS} == {
        TraderLineage.R38_GBPJPY,
        TraderLineage.R43_GBPUSD,
        TraderLineage.R42_AUDJPY,
        TraderLineage.R38_EURUSD,
        TraderLineage.R34_XAUUSD,
        TraderLineage.VT08_FOREX,
        TraderLineage.VT31_NAS100,
    }


def test_train_prior_digest_is_frozen() -> None:
    assert prior_digest_sha256() == (
        "sha256:37ab8533cee83c4854b8dd4472a5d7365d9849915e3972ace5a4a4a62abf6391"
    )


def test_train_prior_converts_structural_r_to_current_stop_risk_usd() -> None:
    expectation = build_frozen_train_expectation(
        trader_id=TraderLineage.VT31_NAS100,
        stop_risk_usd=Decimal("10"),
        as_of=datetime(2026, 9, 27, 14, 0, tzinfo=UTC),
    )
    prior = frozen_train_prior_for(TraderLineage.VT31_NAS100)

    assert expectation.basis is CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR
    assert expectation.expected_net_value_usd == (
        prior.expected_structural_r * Decimal("10")
    )
    assert expectation.expected_capital_minutes == Decimal("6")
    assert expectation.future_market_used is False
    assert expectation.outcome_used is False


def test_train_prior_preserves_negative_train_evidence_without_tuning() -> None:
    eurusd = frozen_train_prior_for(TraderLineage.R38_EURUSD)
    vt08 = frozen_train_prior_for(TraderLineage.VT08_FOREX)

    assert eurusd.expected_structural_r < 0
    assert vt08.expected_structural_r < 0


def test_train_prior_uses_robust_mom_not_arithmetic_mean() -> None:
    eurusd = frozen_train_prior_for(TraderLineage.R38_EURUSD)

    assert eurusd.arithmetic_mean_r_diagnostic > 0
    assert eurusd.expected_structural_r < 0
    assert len(eurusd.chronological_block_means_r) == 5
