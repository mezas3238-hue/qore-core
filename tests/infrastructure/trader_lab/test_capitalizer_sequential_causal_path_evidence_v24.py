from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.trader_lab import (
    capitalizer_hypothesis_survival_model_v21 as v21,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequential_causal_path_evidence_v24 as v24,
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
        "phase": "INVALIDATING",
        "elapsed_full_bars": 5,
        "max_favorable_r": "0.10",
        "close_r": "-0.30",
        "adverse_close_count": 2,
        "invalidating_age": 1,
        "adverse_displacement_observed": True,
        "displacement_midpoint_reclaimed": False,
        "adverse_extreme_extended": False,
        "recovered_since_deterioration": False,
    }
    values.update(overrides)
    return v21.Observation(**values)  # type: ignore[arg-type]


def test_transition_token_is_path_based_and_market_agnostic() -> None:
    previous = _row(
        phase="WEAKENING",
        close_r="-0.20",
        max_favorable_r="0.10",
    )
    current = _row(
        phase="INVALIDATING",
        close_r="-0.28",
        max_favorable_r="0.10",
        adverse_extreme_extended=True,
    )
    token = v24._transition_token(previous, current)
    assert token == (
        "DETERIORATION_TO_INVALIDATING|DETERIORATING|"
        "STALLED_MFE|ADVERSE_EXTENSION"
    )
    assert "EURUSD" not in token
    assert "LONDON" not in token
    assert "LONG" not in token


def test_hierarchy_uses_causal_regime_not_identity() -> None:
    ctx = SimpleNamespace(
        context_signature="M15=ALIGNED|H1=OPPOSED|VOL=NORMAL|DEST=GE_2R",
        regime_signature="M15=ALIGNED|H1=OPPOSED|VOL=NORMAL",
        destination_state="GE_2R",
    )
    levels = v24._hierarchy_keys(ctx)
    assert levels == (
        (
            "R0",
            "M15=ALIGNED|H1=OPPOSED|VOL=NORMAL|DEST=GE_2R",
        ),
        ("R1", "M15=ALIGNED|H1=OPPOSED|VOL=NORMAL"),
        ("R2", "GE_2R"),
        ("R3", "GLOBAL"),
    )


def test_laplace_token_evidence_and_positive_mean() -> None:
    cell = v24.CellStats(
        exit_total=60,
        continue_total=40,
        vocabulary_size=4,
        tokens={
            "T": v24.TokenStats(
                support=35,
                exit_better_occurrences=24,
                continue_better_occurrences=8,
                sum_exit_advantage_r="7.0",
            )
        },
    )
    evidence = v24._token_evidence(cell=cell, token="T")
    assert evidence is not None
    support, bayes_factor, mean_advantage = evidence
    assert support == 35
    expected = ((24 + 1) / (60 + 4)) / ((8 + 1) / (40 + 4))
    assert abs(bayes_factor - expected) < 1e-12
    assert mean_advantage == Decimal("0.2")


def test_common_lookup_requires_support_in_both_models() -> None:
    ctx = SimpleNamespace(
        context_signature="CTX",
        regime_signature="REG",
        destination_state="DEST",
    )
    strong = v24.CellStats(
        exit_total=50,
        continue_total=50,
        vocabulary_size=1,
        tokens={
            "T": v24.TokenStats(
                support=30,
                exit_better_occurrences=20,
                continue_better_occurrences=10,
                sum_exit_advantage_r="3",
            )
        },
    )
    weak = v24.CellStats(
        exit_total=50,
        continue_total=50,
        vocabulary_size=1,
        tokens={
            "T": v24.TokenStats(
                support=29,
                exit_better_occurrences=20,
                continue_better_occurrences=9,
                sum_exit_advantage_r="3",
            )
        },
    )
    model_a: v24.Model = {
        "R0": {"CTX": strong},
        "R1": {"REG": strong},
        "R2": {"DEST": strong},
        "R3": {"GLOBAL": strong},
    }
    model_b: v24.Model = {
        "R0": {"CTX": weak},
        "R1": {"REG": strong},
        "R2": {"DEST": strong},
        "R3": {"GLOBAL": strong},
    }
    level, key, left, right = v24._lookup_common_evidence(
        ctx=ctx,
        token="T",
        model_a=model_a,
        model_b=model_b,
    )
    assert level == "R1"
    assert key == "REG"
    assert left is not None
    assert right is not None
    assert left[0] == 30
    assert right[0] == 30


def test_frozen_v24_constants() -> None:
    assert v24.POLICY == "INVALIDATING_SEQ_BF3_POSMEAN_N30_T3"
    assert v24.MINIMUM_SUPPORT == 30
    assert v24.MINIMUM_SUPPORTED_TRANSITIONS == 3
    assert v24.BAYES_FACTOR_MINIMUM == 3.0
