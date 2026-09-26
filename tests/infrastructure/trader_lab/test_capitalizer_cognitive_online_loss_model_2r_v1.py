from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_online_loss_model_2r_v1 as lab,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_stability_intelligence_2r_v1 as stability,
)


def test_logistic_updates_toward_observed_loss() -> None:
    model = lab.OnlineLogistic()
    tokens = ("A", "B", "C")
    before = model.predict(tokens)
    model.update(tokens, label=1.0)
    after = model.predict(tokens)
    assert before == 0.5
    assert after > before
    assert model.updates == 1


def test_high_loss_probability_routes_to_strong_protection() -> None:
    mode = lab._route_mode(
        policy="BANDIT_MODEL_ROUTE",
        prediction=0.80,
        bandit_mode="ORIGINAL",
    )
    assert mode == "M3_SWING_IMPROVE"


def test_blocking_stays_disabled_during_model_warmup() -> None:
    allow, reason = lab._admit(
        policy="BANDIT_GATE_075_GLOBAL",
        prediction=0.99,
        trained=lab.MIN_TRAINED - 1,
        state=stability.StabilityState.DEFENSIVE,
    )
    assert allow is True
    assert reason == "MODEL_WARMUP"
