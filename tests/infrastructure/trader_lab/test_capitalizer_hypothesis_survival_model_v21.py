from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_state_machine_v20 as v20,
)
from qore.infrastructure.trader_lab import (
    capitalizer_hypothesis_survival_model_v21 as v21,
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


def test_exact_bins_are_frozen() -> None:
    assert v21._elapsed_bin(2) == "E_1_2"
    assert v21._elapsed_bin(3) == "E_3_4"
    assert v21._elapsed_bin(13) == "E_13_PLUS"
    assert v21._mfe_bin(Decimal("0.049")) == "MFE_000_005"
    assert v21._mfe_bin(Decimal("0.20")) == "MFE_020_025"
    assert v21._close_bin(Decimal("-0.75")) == "C_LE_N075"
    assert v21._close_bin(Decimal("-0.05")) == "C_N015_N005"
    assert v21._adverse_bin(3) == "A3_PLUS"
    assert v21._invalidating_age_bin(0) == "I0"


def test_signature_backoff_is_exact_and_has_no_market_identity() -> None:
    row = _row()
    levels = v21._signature_levels(
        row,
        entry_context_family="OTHER",
    )
    assert [level for level, _ in levels] == ["L0", "L1", "L2", "L3", "L4"]
    text = "\n".join(signature for _, signature in levels)
    assert "EURUSD" not in text
    assert "LONDON" not in text
    assert "LONG" not in text
    assert "2026-01-01" not in text
    assert levels[-1][1] == v20.Phase.INVALIDATING.value


def test_beta_one_one_smoothing_and_same_level_support() -> None:
    row = _row()
    levels = dict(
        v21._signature_levels(
            row,
            entry_context_family="OTHER",
        )
    )
    model_a: v21.Model = {
        level: {} for level in ("L0", "L1", "L2", "L3", "L4")
    }
    model_b: v21.Model = {
        level: {} for level in ("L0", "L1", "L2", "L3", "L4")
    }
    model_a["L2"][levels["L2"]] = (30, 5)
    model_b["L2"][levels["L2"]] = (30, 6)

    level, _, support_a, support_b, estimate_a, estimate_b = (
        v21._lookup_agreement(
            row=row,
            entry_context_family="OTHER",
            model_a=model_a,
            model_b=model_b,
            minimum_support=30,
        )
    )
    assert level == "L2"
    assert support_a == 30
    assert support_b == 30
    assert estimate_a == Decimal(6) / Decimal(32)
    assert estimate_b == Decimal(7) / Decimal(32)


def test_policy_family_matches_predeclared_protocol() -> None:
    assert set(v21.POLICY_SPECS) == {
        "INVALIDATING_SURV20_N30_P2",
        "INVALIDATING_SURV25_N30_P2",
        "INVALIDATING_SURV30_N30_P2",
        "WEAK_OR_INVALID_SURV20_N50_P2",
        "WEAK_OR_INVALID_SURV25_N50_P2",
        "WEAK_OR_INVALID_SURV30_N50_P2",
    }
    assert v21.CANONICAL_TRACK == "HSM_BASE"
    assert v21.PERSISTENCE_REQUIRED == 2
    assert v21.DEPARTURE_R == Decimal("0.25")
