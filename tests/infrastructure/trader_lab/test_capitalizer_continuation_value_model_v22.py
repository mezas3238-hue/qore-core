from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_continuation_value_model_v22 as v22,
)
from qore.infrastructure.trader_lab import (
    capitalizer_hypothesis_survival_model_v21 as v21,
)
from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_state_machine_v20 as v20,
)


def _row(**overrides: object) -> v21.Observation:
    values: dict[str, object] = {
        "period": "P",
        "symbol": "EURUSD",
        "session": "LONDON",
        "operating_date": "2026-01-01",
        "side": "LONG",
        "entry_at": "2026-01-01T10:00:00+00:00",
        "observed_at": "2026-01-01T10:05:00+00:00",
        "phase": v20.Phase.INVALIDATING.value,
        "elapsed_full_bars": 5,
        "max_favorable_r": "0.12",
        "close_r": "-0.35",
        "adverse_close_count": 2,
        "invalidating_age": 1,
        "adverse_displacement_observed": True,
        "displacement_midpoint_reclaimed": False,
        "adverse_extreme_extended": True,
        "recovered_since_deterioration": False,
    }
    values.update(overrides)
    return v21.Observation(**values)  # type: ignore[arg-type]


def _value(
    *,
    retracement: str = "0.47",
    velocity: str | None = "-0.10",
) -> v22.ValueObservation:
    return v22.ValueObservation(
        row=_row(),
        retracement_r=retracement,
        velocity_two_bar_r=velocity,
    )


def test_v22_has_one_predeclared_policy() -> None:
    assert v22.POLICY == "INVALIDATING_CV_W95_POSMEAN_N30_P2"
    assert v22.POLICIES == ("SURFACE_CONTROL", v22.POLICY)
    assert v22.MINIMUM_SUPPORT == 30
    assert v22.PERSISTENCE_REQUIRED == 2


def test_retracement_and_velocity_bins_are_frozen() -> None:
    assert v22._retracement_bin(Decimal("0.149")) == "RET_LT_015"
    assert v22._retracement_bin(Decimal("0.15")) == "RET_015_030"
    assert v22._retracement_bin(Decimal("0.30")) == "RET_030_050"
    assert v22._retracement_bin(Decimal("0.50")) == "RET_GE_050"

    assert v22._velocity_bin(None) == "VEL_UNAVAILABLE"
    assert v22._velocity_bin(Decimal("0.05")) == "VEL_IMPROVING"
    assert v22._velocity_bin(Decimal("-0.05")) == "VEL_DETERIORATING"
    assert v22._velocity_bin(Decimal("0.049")) == "VEL_FLAT"


def test_two_bar_velocity_uses_only_completed_prior_observations() -> None:
    rows = (
        _row(
            observed_at="2026-01-01T10:01:00+00:00",
            close_r="-0.10",
        ),
        _row(
            observed_at="2026-01-01T10:02:00+00:00",
            close_r="-0.20",
        ),
        _row(
            observed_at="2026-01-01T10:03:00+00:00",
            close_r="-0.40",
        ),
    )
    augmented = v22._augment_observations(rows)
    assert augmented[0].velocity_two_bar_r is None
    assert augmented[1].velocity_two_bar_r is None
    assert Decimal(augmented[2].velocity_two_bar_r or "0") == Decimal("-0.30")


def test_signature_backoff_has_no_market_identity() -> None:
    levels = v22._signature_levels(
        _value(),
        entry_context_family="OTHER",
    )
    assert [level for level, _ in levels] == [
        "L0",
        "L1",
        "L2",
        "L3",
        "L4",
        "L5",
    ]
    text = "\n".join(signature for _, signature in levels)
    assert "EURUSD" not in text
    assert "LONDON" not in text
    assert "LONG" not in text
    assert "2026-01-01" not in text
    assert levels[-1][1] == v20.Phase.INVALIDATING.value


def test_wilson_requires_statistically_credible_majority() -> None:
    assert v22._wilson_lower(30, 30) > Decimal("0.50")
    assert v22._wilson_lower(16, 30) < Decimal("0.50")


def test_positive_mean_and_wilson_are_both_required() -> None:
    good = v22.SignatureStats(
        support=30,
        beneficial_exits=30,
        sum_exit_advantage_r="3",
    )
    negative_mean = v22.SignatureStats(
        support=30,
        beneficial_exits=30,
        sum_exit_advantage_r="-0.1",
    )
    weak_majority = v22.SignatureStats(
        support=30,
        beneficial_exits=16,
        sum_exit_advantage_r="3",
    )
    assert v22._evidence_passes(good) is True
    assert v22._evidence_passes(negative_mean) is False
    assert v22._evidence_passes(weak_majority) is False


def test_lookup_requires_same_support_qualified_level() -> None:
    item = _value()
    levels = dict(
        v22._signature_levels(
            item,
            entry_context_family="OTHER",
        )
    )
    model_a: v22.Model = {
        level: {} for level in ("L0", "L1", "L2", "L3", "L4", "L5")
    }
    model_b: v22.Model = {
        level: {} for level in ("L0", "L1", "L2", "L3", "L4", "L5")
    }
    stats = v22.SignatureStats(
        support=30,
        beneficial_exits=25,
        sum_exit_advantage_r="2",
    )
    model_a["L2"][levels["L2"]] = stats
    model_b["L2"][levels["L2"]] = stats

    level, signature, left, right = v22._lookup_agreement(
        item=item,
        entry_context_family="OTHER",
        model_a=model_a,
        model_b=model_b,
    )
    assert level == "L2"
    assert signature == levels["L2"]
    assert left == stats
    assert right == stats
