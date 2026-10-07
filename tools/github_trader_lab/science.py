"""Generic scientific battery for normalized GitHub Trader Lab replay reports."""

from __future__ import annotations

import hashlib
import os
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from decimal import Decimal
from typing import Any


def d(value: object) -> Decimal:
    return Decimal(str(value))


def pf(metrics: dict[str, Any]) -> Decimal:
    value = metrics.get("profit_factor")
    if value is not None:
        return d(value)
    wins = int(metrics.get("wins", 0))
    losses = int(metrics.get("losses", 0))
    if wins > 0 and losses == 0:
        return Decimal("Infinity")
    return Decimal("-Infinity")


def _block_summaries(
    values: tuple[float, ...],
    *,
    block_length: int,
) -> dict[int, tuple[tuple[float, float, float, float], ...]]:
    """Precompute circular-block statistics for hot Monte Carlo."""

    n = len(values)
    takes = {block_length}
    tail = n % block_length
    if tail:
        takes.add(tail)

    summaries: dict[
        int,
        tuple[tuple[float, float, float, float], ...],
    ] = {}
    for take in takes:
        rows: list[tuple[float, float, float, float]] = []
        for start in range(n):
            equity = 0.0
            peak = 0.0
            minimum = 0.0
            max_dd = 0.0
            for offset in range(take):
                equity += values[(start + offset) % n]
                if equity > peak:
                    peak = equity
                if equity < minimum:
                    minimum = equity
                dd = peak - equity
                if dd > max_dd:
                    max_dd = dd
            rows.append((equity, peak, minimum, max_dd))
        summaries[take] = tuple(rows)
    return summaries


def fast_block_bootstrap(
    values_raw: list[object] | tuple[object, ...],
    *,
    domain: str,
    paths: int,
    block_length: int = 5,
) -> dict[str, Any]:
    """Deterministic paired circular-block bootstrap for hot research.

    SHA-256 is used once to bind a stable seed to the declared domain. Draws
    then use Python's version-frozen MT19937 implementation rather than hashing
    every block. The resampling family, block length and 10k path count remain
    unchanged.
    """

    values = tuple(float(value) for value in values_raw)
    n = len(values)
    algorithm = "sha256-seeded-mt19937-circular-block-bootstrap-v3"
    if n == 0:
        return {
            "algorithm": algorithm,
            "paths": paths,
            "block_length": block_length,
            "positive_terminal_probability": "0",
            "p05_terminal_r": "0",
            "p50_terminal_r": "0",
            "p95_max_drawdown_r": "0",
        }
    if block_length <= 0:
        raise ValueError("block_length must be positive")

    summaries = _block_summaries(values, block_length=block_length)
    seed = int.from_bytes(
        hashlib.sha256(domain.encode()).digest()[:16],
        "big",
    )
    rng = random.Random(seed)
    randrange = rng.randrange
    terminals: list[float] = []
    drawdowns: list[float] = []
    blocks_per_path = (n + block_length - 1) // block_length
    tail = n % block_length

    for _ in range(paths):
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for block_index in range(blocks_per_path):
            start = randrange(n)
            take = (
                tail
                if tail and block_index == blocks_per_path - 1
                else block_length
            )
            total, local_peak, local_minimum, local_dd = summaries[take][start]

            cross_dd = peak - (equity + local_minimum)
            if cross_dd > max_dd:
                max_dd = cross_dd
            if local_dd > max_dd:
                max_dd = local_dd

            candidate_peak = equity + local_peak
            if candidate_peak > peak:
                peak = candidate_peak
            equity += total

        terminals.append(equity)
        drawdowns.append(max_dd)

    terminals.sort()
    drawdowns.sort()
    positive = sum(value > 0.0 for value in terminals) / paths
    return {
        "algorithm": algorithm,
        "paths": paths,
        "block_length": block_length,
        "seed_sha256": format(seed, "032x"),
        "positive_terminal_probability": format(positive, ".12g"),
        "p05_terminal_r": format(
            terminals[(paths - 1) * 5 // 100],
            ".12g",
        ),
        "p50_terminal_r": format(
            terminals[(paths - 1) * 50 // 100],
            ".12g",
        ),
        "p95_max_drawdown_r": format(
            drawdowns[(paths - 1) * 95 // 100],
            ".12g",
        ),
    }


def _bootstrap_chunk_worker(
    args: tuple[tuple[object, ...], str, int, int, int],
) -> tuple[list[float], list[float], str]:
    values_raw, domain, paths, block_length, chunk_index = args
    values = tuple(float(value) for value in values_raw)
    n = len(values)
    summaries = _block_summaries(values, block_length=block_length)
    seed = int.from_bytes(
        hashlib.sha256(
            f"{domain}:chunk:{chunk_index}".encode()
        ).digest()[:16],
        "big",
    )
    rng = random.Random(seed)
    randrange = rng.randrange
    terminals: list[float] = []
    drawdowns: list[float] = []
    blocks_per_path = (n + block_length - 1) // block_length
    tail = n % block_length

    for _ in range(paths):
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for block_index in range(blocks_per_path):
            start = randrange(n)
            take = (
                tail
                if tail and block_index == blocks_per_path - 1
                else block_length
            )
            total, local_peak, local_minimum, local_dd = summaries[take][start]
            cross_dd = peak - (equity + local_minimum)
            if cross_dd > max_dd:
                max_dd = cross_dd
            if local_dd > max_dd:
                max_dd = local_dd
            candidate_peak = equity + local_peak
            if candidate_peak > peak:
                peak = candidate_peak
            equity += total
        terminals.append(equity)
        drawdowns.append(max_dd)

    return terminals, drawdowns, format(seed, "032x")


def parallel_block_bootstrap(
    values_raw: tuple[object, ...],
    *,
    domain: str,
    paths: int,
    block_length: int,
    workers: int,
) -> dict[str, Any]:
    workers = max(1, min(workers, paths))
    counts = [
        paths // workers + (1 if index < paths % workers else 0)
        for index in range(workers)
    ]
    args = [
        (values_raw, domain, count, block_length, index)
        for index, count in enumerate(counts)
        if count
    ]
    terminals: list[float] = []
    drawdowns: list[float] = []
    seeds: list[str] = []
    with ProcessPoolExecutor(max_workers=len(args)) as pool:
        for chunk_terminals, chunk_drawdowns, seed in pool.map(
            _bootstrap_chunk_worker,
            args,
        ):
            terminals.extend(chunk_terminals)
            drawdowns.extend(chunk_drawdowns)
            seeds.append(seed)

    terminals.sort()
    drawdowns.sort()
    positive = sum(value > 0.0 for value in terminals) / paths
    return {
        "algorithm": (
            "sha256-seeded-mt19937-circular-block-bootstrap-v4-parallel"
        ),
        "paths": paths,
        "block_length": block_length,
        "worker_count": len(args),
        "chunk_seed_sha256": seeds,
        "positive_terminal_probability": format(positive, ".12g"),
        "p05_terminal_r": format(
            terminals[(paths - 1) * 5 // 100],
            ".12g",
        ),
        "p50_terminal_r": format(
            terminals[(paths - 1) * 50 // 100],
            ".12g",
        ),
        "p95_max_drawdown_r": format(
            drawdowns[(paths - 1) * 95 // 100],
            ".12g",
        ),
    }


def _bootstrap_worker(
    args: tuple[tuple[object, ...], str, int, int],
) -> dict[str, Any]:
    values, domain, paths, block_length = args
    return fast_block_bootstrap(
        values,
        domain=domain,
        paths=paths,
        block_length=block_length,
    )


def _existing_monte_carlo(
    row: dict[str, Any],
    *,
    min_paths: int,
) -> dict[str, Any] | None:
    existing = row.get("monte_carlo")
    if (
        isinstance(existing, dict)
        and int(existing.get("paths", 0)) >= min_paths
        and existing.get("positive_terminal_probability") is not None
        and existing.get("p95_max_drawdown_r") is not None
    ):
        return existing
    return None


def temporal_nondegrade(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    left = baseline.get("temporal_blocks", {})
    right = candidate.get("temporal_blocks", {})
    common = sorted(set(left) & set(right))
    details: dict[str, Any] = {}
    all_ok = bool(common)
    for key in common:
        bm = left[key]
        cm = right[key]
        mean_delta = d(cm["mean_r"]) - d(bm["mean_r"])
        dd_ok = d(cm["max_drawdown_r"]) <= d(bm["max_drawdown_r"])
        ok = mean_delta >= 0 and dd_ok
        all_ok &= ok
        details[key] = {
            "mean_r_delta": format(mean_delta, "f"),
            "dd_nondegrade": dd_ok,
            "nondegrade": ok,
        }
    return all_ok, details


def evaluate(
    profile: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    science = profile["science"]
    control = str(science["control"])
    primary_lane = str(science["primary_lane"])
    lanes = tuple(profile["lanes"].keys())
    if primary_lane not in lanes:
        raise ValueError("primary_lane is not a configured lane")

    variant_names = tuple(payloads[lanes[0]]["variants"])
    if control not in variant_names:
        raise ValueError(f"control {control!r} missing")
    for lane in lanes:
        if tuple(payloads[lane]["variants"]) != variant_names:
            raise ValueError("variant identity differs across lanes")

    min_density = d(science["min_density"])
    min_winner_count = d(science["min_winner_count_preservation"])
    min_winner_r = d(science["min_winner_r_preservation"])
    all_lane_pf_floor = d(science["all_lane_pf_floor"])
    hard_dd = d(science["hard_dd_max_r"])
    primary_pf_floor = d(science["primary_pf_floor"])
    primary_mean_floor = d(science["primary_mean_r_floor"])
    mc_paths_min = int(science["mc_paths_min"])
    mc_positive_floor = d(science["mc_positive_floor"])
    mc_p95_dd_max = d(science["mc_p95_dd_max_r"])
    require_temporal = bool(science.get("require_temporal_nondegrade", True))

    mc_required_variants: set[str] = set()
    for variant in variant_names:
        deterministic_pass = True
        for lane in lanes:
            baseline = payloads[lane]["variants"][control]
            candidate = payloads[lane]["variants"][variant]
            bm = baseline["metrics"]
            cm = candidate["metrics"]
            winner = candidate["winner_preservation"]

            temporal_ok, _ = temporal_nondegrade(
                baseline,
                candidate,
            )
            if not require_temporal:
                temporal_ok = True

            deterministic_pass &= (
                pf(cm) >= pf(bm)
                and d(cm["mean_r"]) >= d(bm["mean_r"])
                and d(cm["max_drawdown_r"]) <= d(bm["max_drawdown_r"])
                and d(candidate["relative_density_vs_control"])
                >= min_density
                and d(winner["count"]) >= min_winner_count
                and d(winner["r"]) >= min_winner_r
                and temporal_ok
            )
            if not deterministic_pass:
                break
        if deterministic_pass:
            mc_required_variants.add(variant)

    # The control is always measured even if a malformed profile would make
    # its deterministic self-comparison fail.
    mc_required_variants.add(control)

    mc_cache: dict[tuple[str, str], dict[str, Any]] = {}
    pending_by_series: dict[
        tuple[str, tuple[str, ...]],
        tuple[tuple[object, ...], str, int, int],
    ] = {}
    consumers: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[str, str]],
    ] = {}

    block_length = int(science.get("mc_block_length", 5))
    for lane in lanes:
        for variant in variant_names:
            row = payloads[lane]["variants"][variant]
            if variant not in mc_required_variants:
                mc_cache[(lane, variant)] = {
                    "algorithm": "skipped-after-deterministic-pre-gate-failure",
                    "status": "SKIPPED_PRE_GATE_FAILURE",
                    "paths": 0,
                    "block_length": int(
                        science.get("mc_block_length", 5)
                    ),
                    "positive_terminal_probability": "0",
                    "p05_terminal_r": None,
                    "p50_terminal_r": None,
                    "p95_max_drawdown_r": "Infinity",
                }
                continue
            existing = _existing_monte_carlo(
                row,
                min_paths=mc_paths_min,
            )
            if existing is not None:
                mc_cache[(lane, variant)] = existing
                continue

            values = row.get("net_r_values")
            if not isinstance(values, list):
                raise ValueError(
                    f"{lane}/{variant}: normalized replay missing net_r_values"
                )
            canonical_values = tuple(str(value) for value in values)
            series_key = (lane, canonical_values)
            consumers.setdefault(series_key, []).append((lane, variant))
            if series_key not in pending_by_series:
                paired_domain = (
                    f"qore:github-trader-lab:"
                    f"{profile['profile_id']}:{lane}:"
                    f"n={len(canonical_values)}:paired-v2"
                )
                pending_by_series[series_key] = (
                    canonical_values,
                    paired_domain,
                    mc_paths_min,
                    block_length,
                )

    if pending_by_series:
        requested_workers = max(
            1,
            int(
                science.get(
                    "mc_max_workers",
                    min(4, os.cpu_count() or 1),
                )
            ),
        )
        computed: dict[
            tuple[str, tuple[str, ...]],
            dict[str, Any],
        ] = {}

        if len(pending_by_series) == 1 and requested_workers > 1:
            key, args = next(iter(pending_by_series.items()))
            values, domain, paths, block_length = args
            computed[key] = parallel_block_bootstrap(
                values,
                domain=domain,
                paths=paths,
                block_length=block_length,
                workers=requested_workers,
            )
        else:
            max_workers = min(
                len(pending_by_series),
                requested_workers,
            )
            if max_workers == 1:
                for key, args in pending_by_series.items():
                    computed[key] = _bootstrap_worker(args)
            else:
                with ProcessPoolExecutor(max_workers=max_workers) as pool:
                    futures = {
                        pool.submit(_bootstrap_worker, args): key
                        for key, args in pending_by_series.items()
                    }
                    for future in as_completed(futures):
                        computed[futures[future]] = future.result()

        for series_key, result in computed.items():
            for consumer in consumers[series_key]:
                mc_cache[consumer] = result

    variants: dict[str, Any] = {}
    for variant in variant_names:
        per_lane: dict[str, Any] = {}
        pf_non_count = 0
        mean_non_count = 0
        dd_non_count = 0
        density_count = 0
        winner_all = True
        temporal_all = True
        mc_all = True

        for lane in lanes:
            base = payloads[lane]["variants"][control]
            cand = payloads[lane]["variants"][variant]
            bm = base["metrics"]
            cm = cand["metrics"]
            winner = cand["winner_preservation"]
            mc = mc_cache[(lane, variant)]

            pf_non = pf(cm) >= pf(bm)
            mean_non = d(cm["mean_r"]) >= d(bm["mean_r"])
            dd_non = d(cm["max_drawdown_r"]) <= d(bm["max_drawdown_r"])
            density_ok = d(cand["relative_density_vs_control"]) >= min_density
            winner_ok = (
                d(winner["count"]) >= min_winner_count
                and d(winner["r"]) >= min_winner_r
            )
            temporal_ok, temporal = temporal_nondegrade(base, cand)
            if not require_temporal:
                temporal_ok = True
            mc_ok = (
                int(mc["paths"]) >= mc_paths_min
                and mc.get("positive_terminal_probability") is not None
                and mc.get("p95_max_drawdown_r") is not None
            )

            pf_non_count += int(pf_non)
            mean_non_count += int(mean_non)
            dd_non_count += int(dd_non)
            density_count += int(density_ok)
            winner_all &= winner_ok
            temporal_all &= temporal_ok
            mc_all &= mc_ok

            per_lane[lane] = {
                "metrics": cm,
                "monte_carlo": mc,
                "pf_nondegrade": pf_non,
                "mean_nondegrade": mean_non,
                "dd_nondegrade": dd_non,
                "density_floor_pass": density_ok,
                "winner_floor_pass": winner_ok,
                "temporal_nondegrade": temporal_ok,
                "temporal_blocks": temporal,
                "monte_carlo_complete": mc_ok,
            }

        primary = payloads[primary_lane]["variants"][variant]
        pm = primary["metrics"]
        pmc = mc_cache[(primary_lane, variant)]
        mc_was_run = int(pmc.get("paths", 0)) >= mc_paths_min
        owner = {
            "pf_floor": pf(pm) >= primary_pf_floor,
            "mean_r_floor": d(pm["mean_r"]) >= primary_mean_floor,
            "observed_dd_hard_gate": d(pm["max_drawdown_r"]) <= hard_dd,
            "mc_positive_floor": (
                mc_was_run
                and d(pmc["positive_terminal_probability"])
                >= mc_positive_floor
            ),
            "mc_p95_dd_gate": (
                mc_was_run
                and d(pmc["p95_max_drawdown_r"]) <= mc_p95_dd_max
            ),
        }
        all_lane_pf = all(
            pf(payloads[lane]["variants"][variant]["metrics"]) >= all_lane_pf_floor
            for lane in lanes
        )
        all_lane_dd = all(
            d(payloads[lane]["variants"][variant]["metrics"]["max_drawdown_r"])
            <= hard_dd
            for lane in lanes
        )
        development_survivor = (
            pf_non_count == len(lanes)
            and mean_non_count == len(lanes)
            and dd_non_count == len(lanes)
            and density_count == len(lanes)
            and winner_all
            and temporal_all
            and mc_all
        )
        scientific_pass = (
            development_survivor
            and all_lane_pf
            and all_lane_dd
            and all(owner.values())
        )
        variants[variant] = {
            "lanes": per_lane,
            "pf_nondegrade_lanes": pf_non_count,
            "mean_nondegrade_lanes": mean_non_count,
            "dd_nondegrade_lanes": dd_non_count,
            "density_floor_lanes": density_count,
            "winner_preservation_all_lanes": winner_all,
            "temporal_nondegrade_all_lanes": temporal_all,
            "monte_carlo_complete_all_lanes": mc_all,
            "all_lane_pf_floor_pass": all_lane_pf,
            "all_lane_dd_hard_gate_pass": all_lane_dd,
            "primary_lane_gates": owner,
            "development_survivor": development_survivor,
            "scientific_pass": scientific_pass,
            "promotion_authorized": False,
            "certification_authorized": False,
        }

    return {
        "schema": "qore.github-trader-lab.scientific-battery.v2",
        "profile_id": profile["profile_id"],
        "subject": profile["subject"],
        "lanes": list(lanes),
        "control": control,
        "monte_carlo_required_variants": sorted(mc_required_variants),
        "monte_carlo_skipped_variants": sorted(
            set(variant_names) - mc_required_variants
        ),
        "battery_layers": [
            "MULTI_LANE_REPLAY",
            "FIXED_FRICTION_FROM_SUBJECT_REPLAY",
            "PF_MEAN_DD_NONDEGRADE",
            "DENSITY_FLOOR",
            "WINNER_COUNT_AND_R_PRESERVATION",
            "TEMPORAL_BLOCK_STRESS",
            "DETERMINISTIC_10000_PATH_PAIRED_CIRCULAR_BLOCK_BOOTSTRAP_V4_PARALLEL",
            "CROSS_LANE_PF_FLOOR",
            "OBSERVED_DD_HARD_GATE",
            "PRIMARY_LANE_DIRECTION_GATES",
        ],
        "variants": variants,
        "development_survivors": [
            name for name, row in variants.items() if row["development_survivor"]
        ],
        "hard_dd_survivors": [
            name
            for name, row in variants.items()
            if row["development_survivor"] and row["all_lane_dd_hard_gate_pass"]
        ],
        "scientific_passes": [
            name for name, row in variants.items() if row["scientific_pass"]
        ],
        "governance": {
            "independent_trader_lab": True,
            "research_only": True,
            "fresh_holdout_opened": False,
            "candidate_certified": False,
            "promotion_authorized": False,
            "sovereign_workflow_modified": False,
            "broker_mutation": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
