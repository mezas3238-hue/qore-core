from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_single_bucket_ablation import (
    screen_single_bucket_ablations,
)


def _summary(trades: int, total_r: float) -> dict[str, float | int]:
    return {"trades": trades, "total_r": total_r}


def test_single_bucket_ablation_prefers_globally_negative_bucket() -> None:
    overall = {
        "Y1": _summary(10, -1.0),
        "Y2": _summary(10, 2.0),
    }
    dimensions = {
        "reclaim": {
            "MID": {
                "full_2y": _summary(4, -2.0),
                "annual": {
                    "Y1": _summary(2, -2.0),
                    "Y2": _summary(2, 0.0),
                },
            },
            "OTHER": {
                "full_2y": _summary(16, 3.0),
                "annual": {
                    "Y1": _summary(8, 1.0),
                    "Y2": _summary(8, 2.0),
                },
            },
        }
    }

    candidates = screen_single_bucket_ablations(
        overall_annual=overall,
        dimensions=dimensions,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.dimension == "reclaim"
    assert candidate.label == "MID"
    assert candidate.removes_globally_negative_bucket is True
    assert candidate.residual_trades == 16
    assert candidate.residual_total_r == 3.0
    assert candidate.minimum_annual_r == 1.0


def test_single_bucket_ablation_does_not_reconstruct_path_metrics() -> None:
    overall = {
        "Y1": _summary(5, 1.0),
        "Y2": _summary(5, 1.0),
    }

    assert (
        screen_single_bucket_ablations(
            overall_annual=overall,
            dimensions={},
        )
        == ()
    )
