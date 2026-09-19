"""NAS100 New York journey bifurcation forensics for VT31.

Research-only. Silver Bullet source identity is frozen and is not modified.

The lab observes an executed source after fill and asks what was causally
visible at two earned-progress checkpoints: +0.50R and +1.00R by CLOSED M1.
It then labels the untouched post-checkpoint journey only for research:

- GIVEBACK_BEFORE_DOL1: methodological invalidation before opposite boundary;
- DOL1_ONLY: opposite boundary reached, no +0.25 reference extension;
- DOL2_PLUS_0_25_REF;
- DOL3_PLUS_0_50_REF;
- DOL4_PLUS_1_00_REF;
- DOL5_PLUS_1_50_REF;
- DOL6_PLUS_2_00_REF.

Primary checkpoint features are native M1 / New York journey state only:
time-to-checkpoint, path efficiency, directional close ratio, overlap,
pre-checkpoint MAE, pullback from MFE, body quality, confirmed protective
swings, local/reference sweeps, risk/reference geometry and remaining
distance to DOL1.

Future journey labels are research-only and never runtime inputs.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders import vt31_silver_bullet_r2_2 as silver
from qore.infrastructure.traders.vt31_nas100_cibo_causal_structure import (
    local_sweep_events,
    reference_sweep_events,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.ny_journey_bifurcation_forensics.v1"
IDENTITY = "VT31_NAS100_NY_JOURNEY_BIFURCATION_FORENSICS_V1"
MARKET = "NAS100"
LIFECYCLE_MINUTE = 16 * 60
EXPECTED_SOURCE_SHA256 = (
    "bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf"
)
EXPECTED_METHODOLOGY_ID = "ttrades-am-silver-bullet-nq-r2.2"
CHECKPOINTS = (Decimal("0.50"), Decimal("1.00"))

FEATURE_FIELDS = (
    "minutes_to_checkpoint_bucket",
    "path_efficiency_bucket",
    "directional_close_ratio_bucket",
    "overlap_rate_bucket",
    "mae_before_checkpoint_bucket",
    "pullback_from_mfe_bucket",
    "directional_body_ratio_bucket",
    "protective_swing_count_bucket",
    "local_sweep_count_bucket",
    "reference_sweep_count_bucket",
    "risk_ref_bucket",
    "remaining_to_dol1_r_bucket",
    "checkpoint_clock_bucket",
    "selected_family",
    "side",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _touches_stop(bar: object, side: str, stop: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "low")) <= stop
    return _d(getattr(bar, "high")) >= stop


def _touches_level(bar: object, side: str, level: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def _favorable_close_r(
    bar: object,
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    close = _d(getattr(bar, "close"))
    if side == "long":
        return (close - entry) / risk
    return (entry - close) / risk


def _mfe_r(
    bars: tuple[object, ...],
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    if side == "long":
        extreme = max(_d(getattr(bar, "high")) for bar in bars)
        return (extreme - entry) / risk
    extreme = min(_d(getattr(bar, "low")) for bar in bars)
    return (entry - extreme) / risk


def _mae_r(
    bars: tuple[object, ...],
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    if side == "long":
        extreme = min(_d(getattr(bar, "low")) for bar in bars)
        return max(Decimal(0), (entry - extreme) / risk)
    extreme = max(_d(getattr(bar, "high")) for bar in bars)
    return max(Decimal(0), (extreme - entry) / risk)


def _path_efficiency(
    bars: tuple[object, ...],
    *,
    side: str,
    entry: Decimal,
) -> Decimal:
    if not bars:
        return Decimal(0)
    closes = [entry, *(_d(getattr(bar, "close")) for bar in bars)]
    travelled = sum(
        (abs(closes[index] - closes[index - 1]) for index in range(1, len(closes))),
        Decimal(0),
    )
    if travelled == 0:
        return Decimal(0)
    net = (
        closes[-1] - entry
        if side == "long"
        else entry - closes[-1]
    )
    return max(Decimal(0), net / travelled)


def _directional_close_ratio(
    bars: tuple[object, ...],
    *,
    side: str,
    entry: Decimal,
) -> Decimal:
    if not bars:
        return Decimal(0)
    previous = entry
    favorable = 0
    for bar in bars:
        close = _d(getattr(bar, "close"))
        if (side == "long" and close > previous) or (
            side == "short" and close < previous
        ):
            favorable += 1
        previous = close
    return Decimal(favorable) / Decimal(len(bars))


def _directional_body_ratio(
    bars: tuple[object, ...],
    *,
    side: str,
) -> Decimal:
    if not bars:
        return Decimal(0)
    favorable = 0
    for bar in bars:
        open_ = _d(getattr(bar, "open"))
        close = _d(getattr(bar, "close"))
        if (side == "long" and close > open_) or (
            side == "short" and close < open_
        ):
            favorable += 1
    return Decimal(favorable) / Decimal(len(bars))


def _overlap_rate(bars: tuple[object, ...]) -> Decimal:
    if len(bars) < 2:
        return Decimal(0)
    overlaps = 0
    eligible = 0
    for previous, current in zip(bars, bars[1:], strict=False):
        p_low = _d(getattr(previous, "low"))
        p_high = _d(getattr(previous, "high"))
        c_low = _d(getattr(current, "low"))
        c_high = _d(getattr(current, "high"))
        p_range = p_high - p_low
        c_range = c_high - c_low
        denominator = min(p_range, c_range)
        if denominator <= 0:
            continue
        eligible += 1
        overlap = max(
            Decimal(0),
            min(p_high, c_high) - max(p_low, c_low),
        )
        if overlap / denominator >= Decimal("0.50"):
            overlaps += 1
    if eligible == 0:
        return Decimal(0)
    return Decimal(overlaps) / Decimal(eligible)


def _protective_swing_count(
    bars: tuple[object, ...],
    *,
    side: str,
    entry: Decimal,
) -> int:
    count = 0
    for index in range(2, len(bars)):
        left = bars[index - 2]
        middle = bars[index - 1]
        right = bars[index]
        if side == "long":
            level = _d(getattr(middle, "low"))
            if (
                level > entry
                and level < _d(getattr(left, "low"))
                and level < _d(getattr(right, "low"))
            ):
                count += 1
        else:
            level = _d(getattr(middle, "high"))
            if (
                level < entry
                and level > _d(getattr(left, "high"))
                and level > _d(getattr(right, "high"))
            ):
                count += 1
    return count


def _dol_ladder(setup: Vt31R22ExecutableSetup) -> tuple[Decimal, ...]:
    side = setup.side.value
    boundary = setup.target_price
    width = (
        setup.source_setup.reference.high
        - setup.source_setup.reference.low
    )
    direction = Decimal(1) if side == "long" else Decimal(-1)
    return (
        boundary,
        boundary + direction * width * Decimal("0.25"),
        boundary + direction * width * Decimal("0.50"),
        boundary + direction * width,
        boundary + direction * width * Decimal("1.50"),
        boundary + direction * width * Decimal("2.00"),
    )


def _deepest_dol(
    bars: tuple[object, ...],
    *,
    side: str,
    ladder: tuple[Decimal, ...],
) -> int:
    rank = 0
    for bar in bars:
        for candidate_rank, level in enumerate(ladder, start=1):
            if _touches_level(bar, side, level):
                rank = max(rank, candidate_rank)
    return rank


def _journey_label(rank: int, invalidated: bool) -> str:
    if rank == 0:
        return (
            "GIVEBACK_BEFORE_DOL1"
            if invalidated
            else "NO_DOL1_BY_LIFECYCLE"
        )
    return (
        "DOL1_ONLY"
        if rank == 1
        else "DOL2_PLUS_0_25_REF"
        if rank == 2
        else "DOL3_PLUS_0_50_REF"
        if rank == 3
        else "DOL4_PLUS_1_00_REF"
        if rank == 4
        else "DOL5_PLUS_1_50_REF"
        if rank == 5
        else "DOL6_PLUS_2_00_REF"
    )


def _bucket_ratio(value: Decimal) -> str:
    if value < Decimal("0.25"):
        return "lt_0_25"
    if value < Decimal("0.50"):
        return "0_25_0_50"
    if value < Decimal("0.75"):
        return "0_50_0_75"
    return "ge_0_75"


def _bucket_minutes(value: int) -> str:
    if value <= 3:
        return "0_3m"
    if value <= 7:
        return "4_7m"
    if value <= 15:
        return "8_15m"
    return "16m_plus"


def _bucket_mae(value: Decimal) -> str:
    if value < Decimal("0.25"):
        return "lt_0_25R"
    if value < Decimal("0.50"):
        return "0_25_0_50R"
    if value < Decimal("0.75"):
        return "0_50_0_75R"
    return "ge_0_75R"


def _bucket_pullback(value: Decimal) -> str:
    if value < Decimal("0.15"):
        return "lt_0_15R"
    if value < Decimal("0.30"):
        return "0_15_0_30R"
    if value < Decimal("0.50"):
        return "0_30_0_50R"
    return "ge_0_50R"


def _bucket_count(value: int) -> str:
    return "0" if value == 0 else "1" if value == 1 else "2_plus"


def _bucket_risk_ref(value: Decimal) -> str:
    if value < Decimal("0.25"):
        return "lt_0_25"
    if value < Decimal("0.50"):
        return "0_25_0_50"
    if value < Decimal("0.75"):
        return "0_50_0_75"
    return "ge_0_75"


def _bucket_remaining(value: Decimal) -> str:
    if value <= Decimal("0.50"):
        return "le_0_50R"
    if value <= Decimal("1.00"):
        return "0_50_1_00R"
    if value <= Decimal("2.00"):
        return "1_2R"
    return "gt_2R"


def _clock_bucket(value: datetime) -> str:
    local = value.astimezone(specialist._NY)
    minute = local.hour * 60 + local.minute
    if minute < 10 * 60 + 15:
        return "10_00_10_14"
    if minute < 10 * 60 + 30:
        return "10_15_10_29"
    if minute < 10 * 60 + 45:
        return "10_30_10_44"
    if minute < 11 * 60:
        return "10_45_10_59"
    if minute < 12 * 60:
        return "11_00_11_59"
    return "12_00_plus"


def _selected_setup(
    day_bars: tuple[object, ...],
    *,
    evidence: str,
) -> Vt31R22ExecutableSetup | None:
    reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
    session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
    if len(reference) != 60 or len(session) != 60:
        return None
    policy = Vt31R22ExecutionPolicy()
    prefix = list(reference)
    for bar in session:
        prefix.append(bar)
        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=getattr(bar, "closed_at"),
            m1_candles=cast(Any, tuple(prefix)),
            evidence_fingerprint=evidence,
        )
        if evaluation.setup is None:
            if evaluation.both_sides_swept:
                return None
            continue
        executable, _ = make_executable_setup(evaluation.setup, policy)
        return executable
    return None


def _fill_index(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
) -> int | None:
    for index, bar in enumerate(day_bars):
        opened_at = cast(datetime, getattr(bar, "opened_at"))
        if opened_at < setup.decision_at:
            continue
        if opened_at >= setup.pending_expires_at:
            break
        low = _d(getattr(bar, "low"))
        high = _d(getattr(bar, "high"))
        if low <= setup.entry_price <= high:
            return index
    return None


def _original_end(
    bars: tuple[object, ...],
    *,
    side: str,
    stop: Decimal,
) -> tuple[int, bool]:
    for index, bar in enumerate(bars):
        if _touches_stop(bar, side, stop):
            return index, True
    return len(bars) - 1, False


def _checkpoint_row(
    *,
    partition: str,
    local_day: date,
    setup: Vt31R22ExecutableSetup,
    path: tuple[object, ...],
    checkpoint_r: Decimal,
) -> dict[str, object] | None:
    side = setup.side.value
    entry = setup.entry_price
    risk = setup.initial_risk
    if risk <= 0:
        return None

    checkpoint_index: int | None = None
    for index, bar in enumerate(path):
        if _touches_stop(bar, side, setup.stop_price):
            return None
        if _favorable_close_r(
            bar,
            side=side,
            entry=entry,
            risk=risk,
        ) >= checkpoint_r:
            checkpoint_index = index
            break
    if checkpoint_index is None:
        return None

    observed = path[: checkpoint_index + 1]
    checkpoint_bar = observed[-1]
    checkpoint_at = cast(datetime, getattr(checkpoint_bar, "closed_at"))
    checkpoint_close = _d(getattr(checkpoint_bar, "close"))
    mfe = _mfe_r(observed, side=side, entry=entry, risk=risk)
    mae = _mae_r(observed, side=side, entry=entry, risk=risk)
    close_progress = _favorable_close_r(
        checkpoint_bar,
        side=side,
        entry=entry,
        risk=risk,
    )
    pullback = max(Decimal(0), mfe - close_progress)

    efficiency = _path_efficiency(
        observed,
        side=side,
        entry=entry,
    )
    close_ratio = _directional_close_ratio(
        observed,
        side=side,
        entry=entry,
    )
    body_ratio = _directional_body_ratio(observed, side=side)
    overlap = _overlap_rate(observed)
    swing_count = _protective_swing_count(
        observed,
        side=side,
        entry=entry,
    )

    local_sweeps = local_sweep_events(observed, checkpoint_at)
    reference_sweeps = reference_sweep_events(
        observed,
        setup.source_setup,
        checkpoint_at,
    )

    ladder = _dol_ladder(setup)
    dol_rank_at_checkpoint = _deepest_dol(
        observed,
        side=side,
        ladder=ladder,
    )
    # The decision exists only after checkpoint_bar closes.  Future labels
    # therefore start on the next M1 bar; never reuse checkpoint-bar range.
    future = path[checkpoint_index + 1 :]
    deepest = _deepest_dol(
        future,
        side=side,
        ladder=ladder,
    )
    _, invalidated = _original_end(
        future,
        side=side,
        stop=setup.stop_price,
    )

    ref_width = (
        setup.source_setup.reference.high
        - setup.source_setup.reference.low
    )
    risk_ref = risk / ref_width if ref_width > 0 else Decimal(0)
    if side == "long":
        remaining = max(
            Decimal(0),
            setup.target_price - checkpoint_close,
        ) / risk
    else:
        remaining = max(
            Decimal(0),
            checkpoint_close - setup.target_price,
        ) / risk

    filled_at = cast(datetime, getattr(path[0], "opened_at"))
    minutes_to_checkpoint = int(
        (checkpoint_at - filled_at).total_seconds() // 60
    )

    return {
        "partition": partition,
        "local_date": local_day.isoformat(),
        "side": side,
        "selected_family": setup.selected_family.value,
        "checkpoint_r": format(checkpoint_r, "f"),
        "checkpoint_at": checkpoint_at.astimezone(UTC).isoformat(),
        "minutes_to_checkpoint": minutes_to_checkpoint,
        "minutes_to_checkpoint_bucket": _bucket_minutes(
            minutes_to_checkpoint
        ),
        "path_efficiency": format(efficiency, "f"),
        "path_efficiency_bucket": _bucket_ratio(efficiency),
        "directional_close_ratio": format(close_ratio, "f"),
        "directional_close_ratio_bucket": _bucket_ratio(close_ratio),
        "overlap_rate": format(overlap, "f"),
        "overlap_rate_bucket": _bucket_ratio(overlap),
        "mae_before_checkpoint_r": format(mae, "f"),
        "mae_before_checkpoint_bucket": _bucket_mae(mae),
        "mfe_at_checkpoint_r": format(mfe, "f"),
        "pullback_from_mfe_r": format(pullback, "f"),
        "pullback_from_mfe_bucket": _bucket_pullback(pullback),
        "directional_body_ratio": format(body_ratio, "f"),
        "directional_body_ratio_bucket": _bucket_ratio(body_ratio),
        "protective_swing_count": swing_count,
        "protective_swing_count_bucket": _bucket_count(swing_count),
        "local_sweep_count": len(local_sweeps),
        "local_sweep_count_bucket": _bucket_count(len(local_sweeps)),
        "reference_sweep_count": len(reference_sweeps),
        "reference_sweep_count_bucket": _bucket_count(
            len(reference_sweeps)
        ),
        "risk_ref": format(risk_ref, "f"),
        "risk_ref_bucket": _bucket_risk_ref(risk_ref),
        "remaining_to_dol1_r": format(remaining, "f"),
        "remaining_to_dol1_r_bucket": _bucket_remaining(remaining),
        "checkpoint_clock_bucket": _clock_bucket(checkpoint_at),
        "dol_rank_at_checkpoint": dol_rank_at_checkpoint,
        "future_deepest_dol_rank": deepest,
        "future_journey_label": _journey_label(
            deepest,
            invalidated,
        ),
        "future_runner_ge_dol2": deepest >= 2,
        "future_extended_ge_dol3": deepest >= 3,
        "future_giveback_before_dol1": deepest == 0 and invalidated,
        "future_label_research_only": True,
    }


def _group_stats(rows: list[dict[str, object]]) -> dict[str, object]:
    n = len(rows)
    runner = sum(bool(row["future_runner_ge_dol2"]) for row in rows)
    extended = sum(bool(row["future_extended_ge_dol3"]) for row in rows)
    giveback = sum(
        bool(row["future_giveback_before_dol1"]) for row in rows
    )
    return {
        "sample": n,
        "runner_ge_dol2": runner,
        "runner_rate": (
            "0" if n == 0 else format(Decimal(runner) / Decimal(n), "f")
        ),
        "extended_ge_dol3": extended,
        "extended_rate": (
            "0" if n == 0 else format(Decimal(extended) / Decimal(n), "f")
        ),
        "giveback_before_dol1": giveback,
        "giveback_rate": (
            "0" if n == 0 else format(Decimal(giveback) / Decimal(n), "f")
        ),
        "journey_labels": dict(
            sorted(
                Counter(
                    cast(str, row["future_journey_label"])
                    for row in rows
                ).items()
            )
        ),
    }


def _feature_diagnostics(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for field in FEATURE_FIELDS:
            grouped[f"{field}={row.get(field)}"].append(row)
    return {
        key: _group_stats(items)
        for key, items in sorted(grouped.items())
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    if silver.SOURCE_SHA256 != EXPECTED_SOURCE_SHA256:
        raise AssertionError("Silver Bullet source SHA changed")
    if silver.METHODOLOGY_ID != EXPECTED_METHODOLOGY_ID:
        raise AssertionError("Silver Bullet methodology identity changed")

    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("journey bifurcation requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    observations: list[dict[str, object]] = []
    status: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        setup = _selected_setup(day_bars, evidence=evidence)
        if setup is None:
            status["no-executable-source"] += 1
            continue
        fill_index = _fill_index(day_bars, setup)
        if fill_index is None:
            status["no-fill"] += 1
            continue

        fill_bar = day_bars[fill_index]
        if _touches_stop(
            fill_bar,
            setup.side.value,
            setup.stop_price,
        ):
            status["fill-bar-stop-path-censored"] += 1
            continue
        if _touches_level(
            fill_bar,
            setup.side.value,
            setup.target_price,
        ):
            status["fill-bar-dol1-path-censored"] += 1
            continue

        # Exact intrabar ordering inside the fill M1 is unknowable from OHLC.
        # Journey checkpoints therefore begin with the first complete M1 bar
        # after the fill bar.
        path = tuple(
            bar
            for bar in day_bars[fill_index + 1 :]
            if specialist.baseline._local_minute(bar) < LIFECYCLE_MINUTE
        )
        if not path:
            status["no-fully-post-fill-m1"] += 1
            continue

        for checkpoint in CHECKPOINTS:
            row = _checkpoint_row(
                partition=partition,
                local_day=local_day,
                setup=setup,
                path=path,
                checkpoint_r=checkpoint,
            )
            if row is None:
                status[f"checkpoint-{checkpoint}-not-earned"] += 1
                continue
            if int(cast(int, row["dol_rank_at_checkpoint"])) > 0:
                status[
                    f"checkpoint-{checkpoint}-dol1-already-reached"
                ] += 1
                continue
            observations.append(row)
            status[f"checkpoint-{checkpoint}-earned-pre-dol1"] += 1

    by_checkpoint: dict[str, object] = {}
    for checkpoint in CHECKPOINTS:
        key = format(checkpoint, "f")
        rows = [
            row
            for row in observations
            if row["checkpoint_r"] == key
        ]
        by_checkpoint[key] = {
            "overall": _group_stats(rows),
            "feature_diagnostics": _feature_diagnostics(rows),
        }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "partition": partition,
        "market": MARKET,
        "silver_bullet_freeze": {
            "source_sha256": silver.SOURCE_SHA256,
            "methodology_id": silver.METHODOLOGY_ID,
            "source_module_modified": False,
        },
        "checkpoints": [format(item, "f") for item in CHECKPOINTS],
        "by_checkpoint": by_checkpoint,
        "observations": observations,
        "status_counts": dict(sorted(status.items())),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "silver_bullet_modified": False,
            "m1_ny_journey_only": True,
            "h4_primary_causal_feature": False,
            "h1_trend_primary_causal_feature": False,
            "checkpoint_requires_closed_m1": True,
            "fill_bar_path_ambiguity_fail_closed": True,
            "pre_dol1_checkpoint_only": True,
            "future_starts_after_checkpoint_bar": True,
            "future_journey_labels_research_only": True,
            "future_labels_allowed_at_runtime": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "consumed_evidence_only": True,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "by_checkpoint": payload["by_checkpoint"],
                "status_counts": payload["status_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
