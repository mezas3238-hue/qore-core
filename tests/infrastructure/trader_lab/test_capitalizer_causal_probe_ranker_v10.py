from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import capitalizer_causal_probe_ranker_v10 as lab


def _point(period: str, index: int, value: str) -> lab.ProbePoint:
    x = index / 49.0
    return lab.ProbePoint(
        period=period,
        symbol="NAS100",
        session="NEW_YORK",
        provenance="TEST",
        mode="ORIGINAL",
        regime="NORMAL",
        destination="GE_2R",
        entry_at=f"2026-01-{(index % 28) + 1:02d}T10:{index % 60:02d}:00+00:00",
        vector=(x, x),
        realized_r=value,
    )


def _examples(period: str) -> tuple[lab.ProbePoint, ...]:
    return tuple(
        _point(period, index, "1" if index >= 20 else "-1")
        for index in range(50)
    )


def test_quantile_is_deterministic() -> None:
    values = (1.0, 2.0, 3.0, 4.0, 5.0)
    assert lab._quantile(values, 0.60) == 3.0
    assert lab._quantile(values, 0.90) == 5.0


def test_period_model_uses_leave_one_out_calibration() -> None:
    model = lab._fit_period(_examples("A"), period="A")
    assert model.period == "A"
    assert len(model.loo_scores) == 50
    assert model.tail_support["0.60"] >= lab.MIN_TAIL_SUPPORT
    assert model.tail_mean_r["0.60"] > 0


def test_cross_period_agreement_releases_high_rank_probe() -> None:
    a = lab._fit_period(_examples("A"), period="A")
    b = lab._fit_period(_examples("B"), period="B")
    query = lab.ProbePoint(
        period="HELDOUT",
        symbol="NAS100",
        session="NEW_YORK",
        provenance="TEST",
        mode="ORIGINAL",
        regime="NORMAL",
        destination="GE_2R",
        entry_at="2026-03-01T10:00:00+00:00",
        vector=(1.0, 1.0),
    )
    release, _scores, percentiles, minimum, tail_mean, support = lab._release(
        (a, b),
        point=query,
        policy="RANK_Q60_035",
    )
    assert release == Decimal("0.35")
    assert min(percentiles) == minimum
    assert minimum >= 0.60
    assert tail_mean > 0
    assert support >= lab.MIN_TAIL_SUPPORT


def test_low_rank_probe_stays_defensive() -> None:
    a = lab._fit_period(_examples("A"), period="A")
    b = lab._fit_period(_examples("B"), period="B")
    query = lab.ProbePoint(
        period="HELDOUT",
        symbol="NAS100",
        session="NEW_YORK",
        provenance="TEST",
        mode="ORIGINAL",
        regime="NORMAL",
        destination="GE_2R",
        entry_at="2026-03-01T10:00:00+00:00",
        vector=(0.0, 0.0),
    )
    release, *_rest = lab._release(
        (a, b),
        point=query,
        policy="RANK_Q80_035",
    )
    assert release == Decimal("0.20")
