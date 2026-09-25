"""Single-bucket ablation screening for VT08 CRT PURE forensics.

Given the annual summaries for one already-frozen parent population and annual
summaries for each mutually-classified forensic bucket, this helper asks:

    If exactly one bucket were removed, would every annual Total-R become
    positive, and how much density / Total-R would remain?

This is a screening tool only. Summary subtraction cannot reconstruct PF,
drawdown, path order or losing streak. Any returned ablation must be frozen as
a new candidate and replayed directly before it can be considered evidence.

No automatic promotion, execution or capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SingleBucketAblation:
    dimension: str
    label: str
    removed_trades: int
    removed_total_r: float
    residual_trades: int
    residual_total_r: float
    minimum_annual_r: float
    annual_residuals: tuple[tuple[str, int, float], ...]

    @property
    def removes_globally_negative_bucket(self) -> bool:
        return self.removed_total_r < 0


def _number(summary: dict[str, Any], field: str) -> float:
    value = summary.get(field)
    if value is None:
        return 0.0
    return float(value)


def screen_single_bucket_ablations(
    *,
    overall_annual: dict[str, dict[str, Any]],
    dimensions: dict[str, dict[str, dict[str, Any]]],
    annual_key: str = "annual",
    minimum_residual_trades: int = 1,
) -> tuple[SingleBucketAblation, ...]:
    """Return one-bucket exclusions that leave every annual Total-R positive."""

    if not overall_annual:
        raise ValueError("overall_annual must be non-empty")
    if minimum_residual_trades < 1:
        raise ValueError("minimum_residual_trades must be >= 1")

    candidates: list[SingleBucketAblation] = []
    base_years = tuple(sorted(overall_annual))

    for dimension, labels in sorted(dimensions.items()):
        for label, payload in sorted(labels.items()):
            annual = payload.get(annual_key)
            if not isinstance(annual, dict):
                continue

            residual_rows: list[tuple[str, int, float]] = []
            all_positive = True
            residual_trades = 0
            residual_total_r = 0.0

            for year in base_years:
                base = overall_annual[year]
                removed = annual.get(year, {})
                trades = int(base.get("trades", 0)) - int(
                    removed.get("trades", 0)
                )
                total_r = _number(base, "total_r") - _number(
                    removed,
                    "total_r",
                )
                residual_rows.append((year, trades, round(total_r, 8)))
                residual_trades += trades
                residual_total_r += total_r
                if total_r <= 0:
                    all_positive = False

            if not all_positive or residual_trades < minimum_residual_trades:
                continue

            full_summary = next(
                (
                    value
                    for key, value in payload.items()
                    if key.startswith("full_") and isinstance(value, dict)
                ),
                {},
            )
            removed_trades = int(full_summary.get("trades", 0))
            removed_total_r = _number(full_summary, "total_r")
            minimum_annual_r = min(row[2] for row in residual_rows)

            candidates.append(
                SingleBucketAblation(
                    dimension=dimension,
                    label=label,
                    removed_trades=removed_trades,
                    removed_total_r=round(removed_total_r, 8),
                    residual_trades=residual_trades,
                    residual_total_r=round(residual_total_r, 8),
                    minimum_annual_r=round(minimum_annual_r, 8),
                    annual_residuals=tuple(residual_rows),
                )
            )

    return tuple(
        sorted(
            candidates,
            key=lambda item: (
                not item.removes_globally_negative_bucket,
                -item.residual_trades,
                -item.minimum_annual_r,
                item.dimension,
                item.label,
            ),
        )
    )
