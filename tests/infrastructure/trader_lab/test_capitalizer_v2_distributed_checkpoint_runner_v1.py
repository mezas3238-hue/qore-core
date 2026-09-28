from __future__ import annotations

from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_dynamic_episode_edge_reserve_relief_v2 as v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v2_distributed_checkpoint_runner_v1 as runner,
)


def _seed(
    *,
    symbol: str,
    entry_at: str,
    action: str,
) -> v2.ActionSeed:
    return v2.ActionSeed(
        symbol=symbol,
        entry_at=entry_at,
        action=action,
        source_dynamic_total_delta_r="1",
        source_legacy_dd_relief_r="1",
        source_rollout_profit_factor="1.5",
        source_in_max_dd_descent=True,
    )


def _metrics(
    *,
    pf: str,
    total: str,
    dd: str,
    streak: int = 5,
) -> dict[str, object]:
    return {
        "profit_factor": pf,
        "total_r": total,
        "max_drawdown_r": dd,
        "max_losing_streak": streak,
        "trades": 1000,
    }


def test_runner_identity() -> None:
    assert runner.IDENTITY == (
        "QORE_CAPITALIZER_V2_DISTRIBUTED_CHECKPOINT_RUNNER_V1"
    )


def test_relief_selection_matches_monolithic_v2_rank() -> None:
    baseline = _metrics(pf="1.50", total="100", dd="7")
    current = _metrics(pf="1.70", total="110", dd="6.8")

    first = runner.CandidateProbe(
        seed=_seed(
            symbol="EURUSD",
            entry_at="2024-01-01T10:00:00+00:00",
            action="BE_AFTER_050",
        ),
        metrics=_metrics(pf="1.55", total="103", dd="6.4"),
        invalid=False,
        replayed_trades=10,
    )
    second = runner.CandidateProbe(
        seed=_seed(
            symbol="GBPUSD",
            entry_at="2024-01-02T10:00:00+00:00",
            action="BE_AFTER_075",
        ),
        metrics=_metrics(pf="1.56", total="104", dd="6.2"),
        invalid=False,
        replayed_trades=10,
    )
    probes = (first, second)
    reference = min(
        probes,
        key=lambda probe: v2._relief_rank(
            probe.metrics or {},
            probe.seed,
        ),
    )

    selected = runner._select_next_probe(
        relief_probes=probes,
        reserve_probes=(),
        baseline=baseline,
        current=current,
    )

    assert selected is not None
    assert selected[0] == "RELIEF"
    assert selected[1] == reference


def test_reserve_selection_matches_monolithic_v2_rank() -> None:
    baseline = _metrics(pf="1.50", total="100", dd="7")
    current = _metrics(pf="1.60", total="105", dd="6.8")

    relief = runner.CandidateProbe(
        seed=_seed(
            symbol="EURUSD",
            entry_at="2024-01-01T10:00:00+00:00",
            action="BE_AFTER_050",
        ),
        metrics=_metrics(pf="1.40", total="90", dd="6.0"),
        invalid=False,
        replayed_trades=10,
    )
    first = runner.CandidateProbe(
        seed=_seed(
            symbol="AUDJPY",
            entry_at="2024-01-03T10:00:00+00:00",
            action="BE_AFTER_075",
        ),
        metrics=_metrics(pf="1.61", total="106", dd="6.8"),
        invalid=False,
        replayed_trades=10,
    )
    second = runner.CandidateProbe(
        seed=_seed(
            symbol="USDJPY",
            entry_at="2024-01-04T10:00:00+00:00",
            action="LOCK025_AFTER_075",
        ),
        metrics=_metrics(pf="1.62", total="108", dd="6.8"),
        invalid=False,
        replayed_trades=10,
    )
    reserve = (first, second)
    reference = min(
        reserve,
        key=lambda probe: v2._reserve_rank(
            probe.metrics or {},
            probe.seed,
        ),
    )

    selected = runner._select_next_probe(
        relief_probes=(relief,),
        reserve_probes=reserve,
        baseline=baseline,
        current=current,
    )

    assert selected is not None
    assert selected[0] == "RESERVE"
    assert selected[1] == reference


def test_checkpoint_roundtrip_preserves_committed_plan(
    tmp_path: Path,
) -> None:
    path = tmp_path / "checkpoint.json"
    baseline = _metrics(pf="1.50", total="100", dd="7")
    current = _metrics(pf="1.60", total="105", dd="6.8")
    step = v2.V2Step(
        step=1,
        role="RESERVE",
        symbol="EURUSD",
        entry_at="2024-01-01T10:00:00+00:00",
        action="BE_AFTER_050",
        current_surface_mode_at_application="BE_AFTER_075",
        current_trigger_family_at_application="BE",
        current_trigger_at="2024-01-01T10:05:00+00:00",
        prior_profit_factor="1.50",
        resulting_profit_factor="1.60",
        prior_total_r="100",
        resulting_total_r="105",
        prior_dd_r="7",
        resulting_dd_r="6.8",
        prior_losing_streak=6,
        resulting_losing_streak=5,
    )
    runner._write_checkpoint(
        path,
        runner._checkpoint_payload(
            period="DEVELOPMENT_2024_2026",
            transition_sha256="abc",
            baseline=baseline,
            current=current,
            steps=[step],
            replay_evaluations=12,
            replayed_trade_evaluations=345,
            invalid_trials=2,
            complete=False,
            stop_reason="CHECKPOINT_AFTER_COMMIT",
        ),
    )

    (
        plan,
        steps,
        replay_evaluations,
        replayed_trade_evaluations,
        invalid_trials,
        loaded_metrics,
    ) = runner._load_checkpoint(
        path,
        period="DEVELOPMENT_2024_2026",
        transition_sha256="abc",
        baseline=baseline,
    )

    assert plan == {
        ("EURUSD", "2024-01-01T10:00:00+00:00"): "BE_AFTER_050"
    }
    assert steps == [step]
    assert replay_evaluations == 12
    assert replayed_trade_evaluations == 345
    assert invalid_trials == 2
    assert loaded_metrics == current
